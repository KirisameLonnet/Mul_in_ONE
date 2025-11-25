"""Service for handling Retrieval-Augmented Generation (RAG) functionalities."""

import logging
from pathlib import Path
from uuid import uuid4

import yaml
from langchain_community.document_loaders import BSHTMLLoader
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import AnyHttpUrl, BaseModel, Field

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
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.embedder = self._create_embedder()

    def _load_config(self, config_path: Path) -> dict:
        """Loads the API configuration from the YAML file."""
        logger.info(f"Loading API configuration from: {config_path}")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _create_embedder(self) -> OpenAIEmbeddings:
        """Creates an embedder based on the default API in the config."""
        default_api_name = self.config.get("default_api")
        if not default_api_name:
            raise ValueError("`default_api` not set in api_configuration.yaml")

        api_config = None
        for api in self.config.get("apis", []):
            if api.get("name") == default_api_name:
                api_config = api
                break
        
        if not api_config:
            raise ValueError(f"Default API '{default_api_name}' not found in api_configuration.yaml")

        logger.info(f"Creating embedder for model: {api_config.get('model')}")
        return OpenAIEmbeddings(
            model=api_config.get("model"),
            openai_api_base=api_config.get("base_url"),
            openai_api_key=api_config.get("api_key"),
        )

    async def ingest_url(self, url: AnyHttpUrl, persona_id: int) -> dict:
        """
        Scrapes a URL, generates embeddings, and stores them in a persona-specific
        Milvus collection.
        """
        collection_name = f"persona_{persona_id}_rag"
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
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        split_docs = splitter.split_documents(docs)
        logger.info(f"Document split into {len(split_docs)} chunks.")

        # 3. Create Milvus vector store and add documents
        vector_store = Milvus(
            embedding_function=self.embedder,
            collection_name=collection_name,
            connection_args={"uri": DEFAULT_MILVUS_URI},
            auto_id=True,
        )
        
        logger.info("Adding document chunks to Milvus...")
        doc_ids = await vector_store.aadd_documents(documents=split_docs)
        logger.info(f"Successfully ingested {len(doc_ids)} document chunks into '{collection_name}'.")

        # Clean up cache
        os.remove(filepath)
        
        return {"status": "success", "documents_added": len(doc_ids), "collection_name": collection_name}

