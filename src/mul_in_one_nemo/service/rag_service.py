"""Service for handling Retrieval-Augmented Generation (RAG) functionalities."""

import logging
import uuid
from pathlib import Path
from typing import Callable, List, Optional

import yaml
from langchain_community.document_loaders import BSHTMLLoader
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import AnyHttpUrl
from langchain_core.embeddings import Embeddings

from pymilvus import Collection, connections, utility, FieldSchema, CollectionSchema, DataType

# Import NAT-based adapter for multi-tenant RAG
from .rag_adapter import RagAdapter

try:
    from nat.retriever.milvus.retriever import CollectionNotFoundError
except ImportError:
    CollectionNotFoundError = None

# A temporary copy of web_utils from NeMo-Agent-Toolkit/scripts
# This should be refactored into a common utility module.
# --- Start of web_utils copy ---
import asyncio
import os
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

async def scrape(urls: list[str]) -> tuple[list[dict], list[dict]]:
    """Scrape a list of URLs."""
    async with httpx.AsyncClient() as client:
        reqs = [client.get(url) for url in urls]
        results = await asyncio.gather(*reqs, return_exceptions=True)
    
    data = [
        {"url": str(r.url), "html": r.text}
        for r in results
        if isinstance(r, httpx.Response) and "text/html" in r.headers["content-type"]
    ]
    errs = [{"url": str(r.request.url), "error": str(r)} for r in results if isinstance(r, Exception)]
    return data, errs

def get_file_path_from_url(url: str, base_path: str = "./.tmp/data") -> tuple[str, str]:
    """Get a unique file path for a URL."""
    parsed_url = urlparse(url)
    filename = parsed_url.path.strip("/").replace("/", "_")
    if not filename:
        filename = "index"
    
    dir_path = os.path.join(base_path, parsed_url.netloc)
    return os.path.join(dir_path, filename), dir_path

def cache_html(content: dict, base_path: str = "./.tmp/data") -> tuple[BeautifulSoup, str]:
    """Cache the HTML content of a URL to a file."""
    filepath, dir_path = get_file_path_from_url(content["url"], base_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    
    soup = BeautifulSoup(content["html"], "html.parser")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    return soup, filepath
# --- End of web_utils copy ---


logger = logging.getLogger(__name__)

# Default paths, consider making these configurable
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "personas" / "api_configuration.yaml"
CACHE_BASE_PATH = "./.tmp/data"
DEFAULT_MILVUS_URI = "http://localhost:19530"


class RAGService:
    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        api_config_resolver: Optional[Callable[[Optional[int]], dict]] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        default_top_k: int = 4,
        use_nat_retriever: bool = True,  # Flag to switch to NAT MilvusRetriever
    ):
        """RAG service.

        - Prototype mode: use YAML at `config_path` when `api_config_resolver` is None.
        - Production mode: inject `api_config_resolver(persona_id)->{"model","base_url","api_key","temperature"}`
          to fetch per-tenant/per-persona API settings from DB or SaaS.
        - NAT mode: When use_nat_retriever=True, uses RagAdapter with NAT's MilvusRetriever
        """
        self.config = self._load_config(config_path) if api_config_resolver is None else None
        self._api_config_resolver = api_config_resolver
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_top_k = default_top_k
        self.use_nat_retriever = use_nat_retriever
        
        # Initialize NAT adapter if enabled
        self._rag_adapter: Optional[RagAdapter] = None
        if use_nat_retriever:
            # Create adapter with embedder factory that wraps _create_embedder
            async def embedder_factory(persona_id: int, username: Optional[str]) -> OpenAIEmbeddings:
                return await self._create_embedder(persona_id)
            self._rag_adapter = RagAdapter(
                embedder_factory=embedder_factory,
                milvus_uri=DEFAULT_MILVUS_URI,
            )
            logger.info("RAGService initialized with NAT MilvusRetriever adapter")
        
        # In prototype mode, cache embedder/llm; in production, create per request
        if self.config is not None:
            # YAML mode is synchronous initialization
            self.embedder = self._create_embedder_sync()
            self.llm = self._create_llm_sync()
        else:
            self.embedder = None
            self.llm = None

    def _load_config(self, config_path: Path) -> dict:
        """Loads the API configuration from the YAML file."""
        logger.info(f"Loading API configuration from: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def _resolve_api_config(self, persona_id: Optional[int] = None) -> dict:
        if self._api_config_resolver is not None:
            cfg = await self._api_config_resolver(persona_id)
            if not isinstance(cfg, dict):
                raise ValueError("api_config_resolver must return a dict")
            return cfg
        return self._resolve_api_config_sync(persona_id)

    def _resolve_api_config_sync(self, persona_id: Optional[int] = None) -> dict:
        # YAML prototype fallback
        assert self.config is not None
        default_api_name = self.config.get("default_api")
        if not default_api_name:
            raise ValueError("`default_api` not set in api_configuration.yaml")
        for api in self.config.get("apis", []):
            if api.get("name") == default_api_name:
                return api
        raise ValueError(f"Default API '{default_api_name}' not found in api_configuration.yaml")

    async def _create_embedder(self, persona_id: Optional[int] = None) -> Embeddings:
        """Create embedder from tenant's global embedding config."""
        # Always use tenant's global embedding API profile
        if self._api_config_resolver is None:
            # YAML prototype mode fallback
            api_config = await self._resolve_api_config(persona_id)
        else:
            # Production mode: get tenant embedding config
            api_config = await self._api_config_resolver(persona_id, use_embedding=True)
        
        logger.info(f"Creating embedder for model: {api_config.get('model')}")
        
        base_url = api_config.get("base_url", "")
        
        # 检测提供商类型
        if "generativelanguage.googleapis.com" in base_url:
            # Google Gemini API - 使用原生 SDK
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                logger.info(f"Using Google Gemini embeddings with model: {api_config.get('model')}")
                return GoogleGenerativeAIEmbeddings(
                    model=api_config.get("model"),
                    google_api_key=api_config.get("api_key"),
                )
            except ImportError:
                logger.error("langchain-google-genai not installed. Install with: pip install langchain-google-genai")
                raise RuntimeError("langchain-google-genai package is required for Google Gemini embeddings")
        else:
            # OpenAI 兼容接口
            return OpenAIEmbeddings(
                model=api_config.get("model"),
                openai_api_base=api_config.get("base_url"),
                openai_api_key=api_config.get("api_key"),
                request_timeout=30.0,  # 30秒超时
            )

    def _create_embedder_sync(self, persona_id: Optional[int] = None) -> Embeddings:
        """Create embedder synchronously (for prototype mode)."""
        api_config = self._resolve_api_config_sync(persona_id)
        logger.info(f"Creating embedder for model: {api_config.get('model')}")
        
        base_url = api_config.get("base_url", "")
        
        # 检测提供商类型
        if "generativelanguage.googleapis.com" in base_url:
            # Google Gemini API - 使用原生 SDK
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                logger.info(f"Using Google Gemini embeddings with model: {api_config.get('model')}")
                return GoogleGenerativeAIEmbeddings(
                    model=api_config.get("model"),
                    google_api_key=api_config.get("api_key"),
                )
            except ImportError:
                logger.error("langchain-google-genai not installed. Install with: pip install langchain-google-genai")
                raise RuntimeError("langchain-google-genai package is required for Google Gemini embeddings")
        else:
            # OpenAI 兼容接口
            return OpenAIEmbeddings(
                model=api_config.get("model"),
                openai_api_base=api_config.get("base_url"),
                openai_api_key=api_config.get("api_key"),
                request_timeout=30.0,  # 30秒超时
            )

    async def _create_llm(self, persona_id: Optional[int] = None) -> OpenAI:
        """Create LLM from resolved API config (per persona when provided)."""
        api_config = await self._resolve_api_config(persona_id)
        logger.info(f"Creating LLM for model: {api_config.get('model')}")
        return OpenAI(
            model=api_config.get("model"),
            openai_api_base=api_config.get("base_url"),
            openai_api_key=api_config.get("api_key"),
            temperature=api_config.get("temperature", 0.4),
        )

    def _create_llm_sync(self, persona_id: Optional[int] = None) -> OpenAI:
        """Create LLM synchronously (for prototype mode)."""
        api_config = self._resolve_api_config_sync(persona_id)
        logger.info(f"Creating LLM for model: {api_config.get('model')}")
        return OpenAI(
            model=api_config.get("model"),
            openai_api_base=api_config.get("base_url"),
            openai_api_key=api_config.get("api_key"),
            temperature=api_config.get("temperature", 0.4),
        )

    def _create_collection(self, collection_name: str, dim: int):
        """Creates a Milvus collection with the standard schema."""
        logger.info(f"Creating collection {collection_name} with dim={dim}")
        
        fields = [
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
        ]
        
        schema = CollectionSchema(fields=fields, description=f"RAG store for {collection_name}", enable_dynamic_field=True)
        collection = Collection(name=collection_name, schema=schema)
        
        # Create index
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 1024},
        }
        collection.create_index(field_name="vector", index_params=index_params)
        collection.load()
        logger.info(f"Collection {collection_name} created and loaded.")

    async def ingest_url(self, url: str, persona_id: int, username: str) -> dict:
        """
        Fetch content from a URL, generate embeddings, and store them in a persona-specific
        Milvus collection.
        """
        collection_name = f"{username}_persona_{persona_id}_rag"
        logger.info(f"Starting ingestion for URL: {url} into collection: {collection_name}")

        # 1. Scrape and cache the URL content
        html_data, errs = await scrape([str(url)])
        if errs:
            logger.error(f"Failed to scrape {url}: {errs[0]['error']}")
            raise RuntimeError(f"Failed to scrape URL: {url}")
        
        _, filepath = cache_html(html_data[0], CACHE_BASE_PATH)
        logger.info(f"URL content cached to: {filepath}")

        # 2. Load, parse, and split the document
        loader = BSHTMLLoader(filepath)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        split_docs = splitter.split_documents(docs)
        logger.info(f"Document split into {len(split_docs)} chunks.")

        # 3. Create Milvus vector store and add documents
        if self.embedder:
            embedder = self.embedder
        else:
            embedder = await self._create_embedder(persona_id)

        # Generate embeddings and prepare data for manual insertion
        logger.info("Generating embeddings for document chunks...")
        embeddings = await embedder.aembed_documents([d.page_content for d in split_docs])
        try:
            import numpy as np
            arr = np.asarray(embeddings, dtype=float)
            logger.info(f"Embeddings array shape: {arr.shape}")
            if arr.ndim != 2:
                raise ValueError(f"Embeddings must be 2D, got shape {arr.shape}")
            if arr.shape[0] != len(split_docs):
                raise ValueError(
                    f"Embedding row count {arr.shape[0]} != chunk count {len(split_docs)}. Do not reshape; one vector per chunk."
                )
            embeddings = arr.tolist()
        except Exception as e:
            logger.warning(f"Embeddings normalization warning: {e}. Proceeding with raw embeddings list.")
        # Some providers may return multiple embeddings per input (e.g., variants).
        # Ensure one embedding per chunk to match Milvus num_rows.
        if len(embeddings) != len(split_docs):
            try:
                if len(embeddings) % len(split_docs) == 0:
                    group_size = len(embeddings) // len(split_docs)
                    logger.warning(
                        f"Embedding count {len(embeddings)} != chunks {len(split_docs)}; "
                        f"group_size={group_size}, taking first embedding of each group"
                    )
                    embeddings = [embeddings[i * group_size] for i in range(len(split_docs))]
                else:
                    logger.warning(
                        f"Embedding count {len(embeddings)} mismatches chunks {len(split_docs)}; "
                        "truncating to chunk count"
                    )
                    embeddings = embeddings[:len(split_docs)]
            except Exception:
                embeddings = embeddings[:len(split_docs)]
        
        # Connect to Milvus and insert with manual UUIDs
        connections.connect(alias="default", uri=DEFAULT_MILVUS_URI)
        
        # Ensure collection exists
        if not utility.has_collection(collection_name):
            if not embeddings:
                logger.warning("No embeddings generated, cannot infer dimension to create collection.")
                raise ValueError("No embeddings to infer dimension for new collection")
            dim = len(embeddings[0])
            self._create_collection(collection_name, dim)

        collection = Collection(collection_name)
        
        # Prepare data with string UUIDs
        doc_ids = [str(uuid.uuid4()) for _ in split_docs]
        texts = [d.page_content for d in split_docs]
        sources = [d.metadata.get("source", "unknown") for d in split_docs]
        
        logger.info(f"Adding {len(doc_ids)} document chunks to Milvus...")
        # Safety checks to ensure one vector per chunk and equal column lengths
        len_ids = len(doc_ids)
        len_vecs = len(embeddings)
        len_texts = len(texts)
        len_srcs = len(sources)
        if not (len_ids == len_vecs == len_texts == len_srcs):
            logger.error(
                f"Column length mismatch before insert: ids={len_ids} vecs={len_vecs} texts={len_texts} srcs={len_srcs}"
            )
            raise ValueError("Column length mismatch: ensure one embedding per chunk")

        # Column-based insert required by Milvus: [document_id, vector, text, source]
        data_columns = [doc_ids, embeddings, texts, sources]
        logger.info(
            f"Inserting data columns: cols={len(data_columns)} rows={len(doc_ids)} into {collection_name}"
        )
        collection.insert(data_columns)
        collection.flush()
        logger.info(f"Successfully ingested {len(doc_ids)} document chunks into '{collection_name}'.")

        # Clean up cache
        os.remove(filepath)
        
        return {"status": "success", "documents_added": len(doc_ids), "collection_name": collection_name}

    async def ingest_text(self, text: str, persona_id: int, username: str, source: Optional[str] = None, expected_dim: Optional[int] = None) -> dict:
        """
        Ingests raw text, generates embeddings, and stores them in a persona-specific
        Milvus collection.
        """
        if source is None:
            source = "raw_text"
        collection_name = f"{username}_persona_{persona_id}_rag"
        logger.info(f"Starting ingestion for text (source={source}) into collection: {collection_name}")

        # 1. Create Document object
        doc = Document(page_content=text, metadata={"source": source})

        # 2. Split the document
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        split_docs = splitter.split_documents([doc])
        logger.info(f"Text split into {len(split_docs)} chunks.")

        # 3. Create Milvus vector store and add documents
        if self.embedder:
            embedder = self.embedder
        else:
            embedder = await self._create_embedder(persona_id)

        # Generate embeddings and prepare data for manual insertion
        logger.info("Generating embeddings for document chunks...")
        embeddings = await embedder.aembed_documents([d.page_content for d in split_docs])
        try:
            import numpy as np
            arr = np.asarray(embeddings, dtype=float)
            logger.info(f"Embeddings array shape: {arr.shape}")
            if arr.ndim != 2:
                raise ValueError(f"Embeddings must be 2D, got shape {arr.shape}")
            if arr.shape[0] != len(split_docs):
                raise ValueError(
                    f"Embedding row count {arr.shape[0]} != chunk count {len(split_docs)}. Do not reshape; one vector per chunk."
                )
            if expected_dim is not None and arr.shape[1] != expected_dim:
                raise ValueError(
                    f"Embedding dim {arr.shape[1]} != expected_dim {expected_dim}. Please adjust model or expected_dim."
                )
            embeddings = arr.tolist()
        except Exception as e:
            logger.warning(f"Embeddings normalization warning: {e}. Proceeding with raw embeddings list.")
        
        # Connect to Milvus and insert with manual UUIDs
        connections.connect(alias="default", uri=DEFAULT_MILVUS_URI)
        
        # Ensure collection exists
        if not utility.has_collection(collection_name):
            if not embeddings:
                logger.warning("No embeddings generated, cannot infer dimension to create collection.")
                raise ValueError("No embeddings to infer dimension for new collection")
            dim = len(embeddings[0])
            self._create_collection(collection_name, dim)

        collection = Collection(collection_name)
        
        # Prepare data with string UUIDs
        doc_ids = [str(uuid.uuid4()) for _ in split_docs]
        texts = [d.page_content for d in split_docs]
        sources = [d.metadata.get("source", source) for d in split_docs]
        
        logger.info(f"Adding {len(doc_ids)} document chunks to Milvus...")
        # Safety checks to ensure one vector per chunk and equal column lengths
        len_ids = len(doc_ids)
        len_vecs = len(embeddings)
        len_texts = len(texts)
        len_srcs = len(sources)
        if not (len_ids == len_vecs == len_texts == len_srcs):
            logger.error(
                f"Column length mismatch before insert: ids={len_ids} vecs={len_vecs} texts={len_texts} srcs={len_srcs}"
            )
            raise ValueError("Column length mismatch: ensure one embedding per chunk")

        # Column-based insert required by Milvus: [document_id, vector, text, source]
        data_columns = [doc_ids, embeddings, texts, sources]
        logger.info(
            f"Inserting data columns: cols={len(data_columns)} rows={len(doc_ids)} into {collection_name}"
        )
        collection.insert(data_columns)
        collection.flush()
        logger.info(f"Successfully ingested {len(doc_ids)} document chunks into '{collection_name}'.")
        
        return {"status": "success", "documents_added": len(doc_ids), "collection_name": collection_name}

    async def delete_documents_by_source(self, persona_id: int, username: str, source: str) -> None:
        """
        Deletes documents from the persona's collection matching a specific source.
        """
        from pymilvus import utility
        
        collection_name = f"{username}_persona_{persona_id}_rag"
        logger.info(f"Attempting to delete documents with source='{source}' from {collection_name}")

        try:
            # Connect to Milvus
            connections.connect(alias="default", uri=DEFAULT_MILVUS_URI)

            # Check if collection exists
            if not utility.has_collection(collection_name):
                logger.info(f"Collection '{collection_name}' does not exist. Skipping delete.")
                return

            # Get the collection
            collection = Collection(name=collection_name)
            
            if collection.num_entities == 0:
                logger.info(f"Collection '{collection_name}' is empty. No documents to delete.")
                return

            # Delete documents using the expression
            # Milvus delete operation is synchronous by nature in PyMilvus client
            # Note: For Milvus 2.3.x, we need to delete by primary key
            # First query to get IDs, then delete by IDs
            expr = f'source == "{source}"'
            query_results = collection.query(expr=expr, output_fields=["document_id"])
            if not query_results:
                logger.info(f"No documents found with source='{source}' in '{collection_name}'.")
                return
            
            ids_to_delete = [r["document_id"] for r in query_results]
            delete_expr = f"document_id in {ids_to_delete}"
            delete_result = collection.delete(delete_expr)
            
            logger.info(f"Successfully deleted {delete_result.delete_count} documents from '{collection_name}' with expression: '{expr}'.")

        except Exception as e:
            logger.error(f"Failed to delete documents by source in collection '{collection_name}': {e}")
            # Do not re-raise, just log, to avoid breaking the main flow on deletion failure


    async def delete_collection(self, persona_id: int, username: str) -> None:
        """
        Deletes the entire Milvus collection for a specific persona.
        """
        from pymilvus import utility
        
        collection_name = f"{username}_persona_{persona_id}_rag"
        logger.info(f"Attempting to delete collection: {collection_name}")

        try:
            # Connect to Milvus
            connections.connect(alias="default", uri=DEFAULT_MILVUS_URI)

            # Check if collection exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                logger.info(f"Successfully dropped collection: {collection_name}")
            else:
                logger.info(f"Collection '{collection_name}' does not exist. Skipping drop.")

        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            # Do not re-raise, just log


    async def _create_retriever(self, persona_id: int, username: str, top_k: Optional[int] = None) -> Milvus:
        """
        Create a Milvus retriever for a specific persona.
        """
        if top_k is None:
            top_k = self.default_top_k
        collection_name = f"{username}_persona_{persona_id}_rag"
        logger.info(f"Creating retriever for collection: {collection_name}")
        
        # Create Milvus vector store and retriever
        if self.embedder:
            embedder = self.embedder
        else:
            embedder = await self._create_embedder(persona_id)
            
        vector_store = Milvus(
            embedding_function=embedder,
            collection_name=collection_name,
            connection_args={"uri": DEFAULT_MILVUS_URI},
        )
        
        return vector_store.as_retriever(search_kwargs={"k": top_k})

    async def retrieve_documents(self, query: str, persona_id: int, username: str, top_k: int = 4) -> List[Document]:
        """
        Retrieve relevant documents from Milvus for a given query and persona.
        
        Uses NAT's MilvusRetriever via RagAdapter when use_nat_retriever=True,
        otherwise falls back to legacy langchain_milvus.Milvus implementation.
        """
        logger.info(
            f"Retrieving documents: user={username}, persona={persona_id}, "
            f"query='{query[:50]}...', top_k={top_k}, nat_mode={self.use_nat_retriever}"
        )
        
        try:
            if self.use_nat_retriever and self._rag_adapter:
                # Use NAT adapter (modern approach)
                docs = await self._rag_adapter.search_as_documents(
                    query=query,
                    username=username,
                    persona_id=persona_id,
                    top_k=top_k,
                )
            else:
                # Legacy langchain_milvus approach
                retriever = await self._create_retriever(persona_id, username, top_k)
                docs = await retriever.ainvoke(query)
            
            logger.info(f"Retrieved {len(docs)} documents")
            return docs
            
        except Exception as e:
            # Handle missing collection gracefully (return empty results)
            is_collection_not_found = False
            if CollectionNotFoundError and isinstance(e, CollectionNotFoundError):
                is_collection_not_found = True
            elif "Collection" in str(e) and "does not exist" in str(e):
                is_collection_not_found = True
            
            if is_collection_not_found:
                logger.warning(f"Collection not found for user={username} persona={persona_id}. Returning empty results.")
                return []

            logger.error(f"Failed to retrieve documents: {e}", exc_info=True)
            raise

    def _format_docs(self, docs: List[Document]) -> str:
        """
        Format documents into a string for use in the prompt.
        """
        return "\n\n".join(doc.page_content for doc in docs)

    async def generate_response(self, query: str, persona_id: int, username: str, persona_prompt: str = "", top_k: int = 4) -> str:
        """
        Generate a response using RAG for a given query and persona.
        """
        logger.info(f"Generating response for query: {query} for persona_id: {persona_id} user: {username}")
        
        try:
            # Retrieve relevant documents
            docs = await self.retrieve_documents(query, persona_id, username, top_k)
            
            # Create prompt template
            template = """{persona_prompt}

Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

{context}

Question: {question}
Helpful Answer:"""
            
            prompt = PromptTemplate.from_template(template)
            
            # Create chain
            if self.llm:
                llm = self.llm
            else:
                llm = await self._create_llm(persona_id)
                
            chain = (
                {"context": lambda x: self._format_docs(x["docs"]), "question": lambda x: x["question"], "persona_prompt": lambda x: x["persona_prompt"]}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            # Generate response
            response = await chain.ainvoke({"docs": docs, "question": query, "persona_prompt": persona_prompt})
            logger.info("Generated response successfully")
            
            return response
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise

