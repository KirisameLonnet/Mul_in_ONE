"""Multi-tenant RAG adapter using NAT's official MilvusRetriever.

This adapter bridges the gap between multi-tenant requirements and NAT's standard components:
- Dynamically resolves collection names based on tenant_id and persona_id
- Creates per-request MilvusRetriever instances for thread safety
- Resolves tenant-specific embedder configurations from the database
- Ensures tenant isolation through collection-level separation
"""

import logging
from typing import Callable, Optional

from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from pymilvus import MilvusClient

from nat.retriever.milvus.retriever import MilvusRetriever
from nat.retriever.models import RetrieverOutput

logger = logging.getLogger(__name__)

DEFAULT_MILVUS_URI = "http://localhost:19530"


class RagAdapter:
    """Adapter for multi-tenant RAG using NAT's MilvusRetriever.
    
    This adapter follows the migration plan's recommendations:
    - Per-request retriever instantiation (avoids concurrency issues)
    - Shared MilvusClient for connection pooling
    - Dynamic collection name resolution
    - Tenant-specific embedder injection
    """

    def __init__(
        self,
        embedder_factory: Callable[[int, Optional[str]], Embeddings],
        milvus_uri: str = DEFAULT_MILVUS_URI,
    ):
        """Initialize the RAG adapter.
        
        Args:
            embedder_factory: Async callable that returns Embeddings for a given 
                             (persona_id, tenant_id). Should resolve from DB config.
            milvus_uri: Milvus connection URI
        """
        self.embedder_factory = embedder_factory
        self.milvus_uri = milvus_uri
        # Shared client for connection pooling (lightweight object creation per request)
        self._client = MilvusClient(uri=milvus_uri)
        logger.info(f"RagAdapter initialized with Milvus URI: {milvus_uri}")

    def _get_collection_name(self, tenant_id: str, persona_id: int) -> str:
        """Generate collection name following multi-tenant convention.
        
        Format: {tenant_id}_persona_{persona_id}_rag
        """
        return f"{tenant_id}_persona_{persona_id}_rag"

    async def search(
        self,
        query: str,
        tenant_id: str,
        persona_id: int,
        top_k: int = 5,
        filters: Optional[str] = None,
    ) -> RetrieverOutput:
        """Perform multi-tenant RAG search using NAT's MilvusRetriever.
        
        This method:
        1. Resolves tenant-specific collection name
        2. Creates tenant-specific embedder
        3. Instantiates a new MilvusRetriever (per-request, thread-safe)
        4. Executes search and returns results
        
        Args:
            query: Search query text
            tenant_id: Tenant identifier for isolation
            persona_id: Persona identifier within tenant
            top_k: Maximum number of results to return
            filters: Optional Milvus filter expression
            
        Returns:
            RetrieverOutput with search results
            
        Raises:
            CollectionNotFoundError: If the collection doesn't exist
            RetrieverError: On other retrieval errors
        """
        collection_name = self._get_collection_name(tenant_id, persona_id)
        logger.info(
            f"RAG search: tenant={tenant_id}, persona={persona_id}, "
            f"collection={collection_name}, query='{query[:50]}...', top_k={top_k}"
        )

        # Resolve tenant-specific embedder configuration
        embedder = await self.embedder_factory(persona_id, tenant_id)

        # Create per-request retriever instance (lightweight, thread-safe)
        # The shared MilvusClient handles connection pooling
        retriever = MilvusRetriever(
            client=self._client,
            embedder=embedder,
            content_field="text",  # Match your Milvus schema
        )

        # Execute search with dynamic parameters
        result = await retriever.search(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            filters=filters,
        )

        logger.info(f"Retrieved {len(result.results)} documents for query")
        return result

    async def search_as_documents(
        self,
        query: str,
        tenant_id: str,
        persona_id: int,
        top_k: int = 5,
        filters: Optional[str] = None,
    ) -> list[Document]:
        """Convenience method returning LangChain Document format.
        
        Wraps search() and converts NAT's RetrieverOutput to Document list
        for backward compatibility with existing code.
        """
        result = await self.search(query, tenant_id, persona_id, top_k, filters)
        
        # Convert NAT Document format to LangChain Document
        documents = []
        for doc in result.results:
            documents.append(
                Document(
                    page_content=doc.page_content,
                    metadata=doc.metadata or {},
                )
            )
        return documents

    def close(self):
        """Close the shared MilvusClient connection."""
        if hasattr(self._client, 'close'):
            self._client.close()
            logger.info("RagAdapter closed Milvus client")
