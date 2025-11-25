"""RAG (Retrieval Augmented Generation) service for persona background knowledge.

This module provides RAG capabilities for enriching persona responses with
relevant background information from their knowledge base. This is particularly
useful for personas with extensive backgrounds or histories that are too long
to include in every prompt.

Example use cases:
- Personas with detailed life histories/experiences
- Characters with extensive world knowledge or backstories
- Expert personas with large knowledge bases

The RAG service uses in-memory vector storage by default, with optional
support for persistent storage via Milvus or other vector databases.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Constants
CHUNK_ID_LENGTH = 16  # Length of truncated SHA256 hash for chunk IDs


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge from a persona's background."""

    content: str
    source: str
    chunk_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(
        cls,
        content: str,
        source: str = "background",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "KnowledgeChunk":
        """Create a knowledge chunk from text content."""
        chunk_id = hashlib.sha256(f"{source}:{content}".encode()).hexdigest()[:CHUNK_ID_LENGTH]
        return cls(
            content=content,
            source=source,
            chunk_id=chunk_id,
            metadata=metadata or {},
        )


class SimpleEmbeddings(Embeddings):
    """Simple character-based embeddings for testing without external API.

    This is a fallback embedding implementation that doesn't require
    external API calls. For production use, replace with proper
    embeddings like OpenAIEmbeddings or NVIDIAEmbeddings.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return [self._embed_single(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a query text."""
        return self._embed_single(text)

    def _embed_single(self, text: str) -> List[float]:
        """Create a simple embedding from text using character frequencies."""
        # Normalize text
        text = text.lower()

        # Create a basic embedding based on character n-gram frequencies
        embedding = [0.0] * self.dimension

        # Use character-level features
        for i, char in enumerate(text):
            # Hash character to dimension index
            idx = ord(char) % self.dimension
            embedding[idx] += 1.0 / (i + 1)  # Position-weighted frequency

        # Normalize the embedding
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding


class InMemoryVectorStore:
    """Simple in-memory vector store for RAG.

    This provides a lightweight vector store that doesn't require
    external dependencies like Milvus. Suitable for development
    and small-scale deployments.
    """

    def __init__(self, embeddings: Embeddings) -> None:
        self.embeddings = embeddings
        self._documents: Dict[str, Document] = {}
        self._vectors: Dict[str, List[float]] = {}

    def add_documents(self, documents: Sequence[Document]) -> List[str]:
        """Add documents to the vector store."""
        ids = []
        texts = [doc.page_content for doc in documents]
        vectors = self.embeddings.embed_documents(texts)

        for doc, vector in zip(documents, vectors):
            doc_id = doc.metadata.get("chunk_id", hashlib.sha256(doc.page_content.encode()).hexdigest()[:16])
            self._documents[doc_id] = doc
            self._vectors[doc_id] = vector
            ids.append(doc_id)

        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
    ) -> List[Document]:
        """Search for similar documents."""
        if not self._documents:
            return []

        query_vector = self.embeddings.embed_query(query)
        scores = []

        for doc_id, doc_vector in self._vectors.items():
            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(query_vector, doc_vector))
            scores.append((doc_id, dot_product))

        # Sort by similarity (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top k documents
        results = []
        for doc_id, _ in scores[:k]:
            results.append(self._documents[doc_id])

        return results

    def delete(self, ids: List[str]) -> None:
        """Delete documents by their IDs."""
        for doc_id in ids:
            self._documents.pop(doc_id, None)
            self._vectors.pop(doc_id, None)

    def clear(self) -> None:
        """Clear all documents from the store."""
        self._documents.clear()
        self._vectors.clear()


@dataclass
class PersonaKnowledgeBase:
    """Knowledge base for a single persona.

    Manages the background knowledge documents for a persona,
    including chunking, embedding, and retrieval.
    """

    persona_handle: str
    vector_store: InMemoryVectorStore
    text_splitter: RecursiveCharacterTextSplitter = field(
        default_factory=lambda: RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
    )
    _chunk_count: int = field(default=0, init=False)

    def add_background(
        self,
        content: str,
        source: str = "background",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Add background knowledge for the persona.

        Args:
            content: The background text to add
            source: Source identifier (e.g., "backstory", "world_knowledge")
            metadata: Additional metadata for the chunks

        Returns:
            List of chunk IDs that were added
        """
        # Split content into chunks
        chunks = self.text_splitter.split_text(content)

        # Create documents with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "persona_handle": self.persona_handle,
                "source": source,
                "chunk_index": self._chunk_count + i,
                **(metadata or {}),
            }
            doc = Document(
                page_content=chunk,
                metadata=chunk_metadata,
            )
            doc.metadata["chunk_id"] = hashlib.sha256(
                f"{self.persona_handle}:{source}:{chunk}".encode()
            ).hexdigest()[:16]
            documents.append(doc)

        # Add to vector store
        ids = self.vector_store.add_documents(documents)
        self._chunk_count += len(chunks)

        return ids

    def retrieve(
        self,
        query: str,
        k: int = 3,
    ) -> List[Document]:
        """Retrieve relevant background knowledge for a query.

        Args:
            query: The query text (e.g., current conversation context)
            k: Number of chunks to retrieve

        Returns:
            List of relevant documents
        """
        return self.vector_store.similarity_search(query, k=k)

    def clear(self) -> None:
        """Clear all knowledge from this persona's knowledge base."""
        self.vector_store.clear()
        self._chunk_count = 0


class RAGService:
    """Central RAG service managing knowledge bases for all personas.

    This service coordinates RAG operations across multiple personas,
    providing a unified interface for adding knowledge and retrieving
    relevant context during conversations.
    """

    def __init__(
        self,
        embeddings: Optional[Embeddings] = None,
    ) -> None:
        """Initialize the RAG service.

        Args:
            embeddings: Embedding model to use. Defaults to SimpleEmbeddings.
        """
        self.embeddings = embeddings or SimpleEmbeddings()
        self._knowledge_bases: Dict[str, PersonaKnowledgeBase] = {}

    def get_or_create_knowledge_base(
        self,
        persona_handle: str,
    ) -> PersonaKnowledgeBase:
        """Get or create a knowledge base for a persona.

        Args:
            persona_handle: The unique handle of the persona

        Returns:
            The persona's knowledge base
        """
        if persona_handle not in self._knowledge_bases:
            vector_store = InMemoryVectorStore(self.embeddings)
            self._knowledge_bases[persona_handle] = PersonaKnowledgeBase(
                persona_handle=persona_handle,
                vector_store=vector_store,
            )
        return self._knowledge_bases[persona_handle]

    def add_persona_background(
        self,
        persona_handle: str,
        content: str,
        source: str = "background",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Add background knowledge for a persona.

        Args:
            persona_handle: The unique handle of the persona
            content: The background text to add
            source: Source identifier
            metadata: Additional metadata

        Returns:
            List of chunk IDs that were added
        """
        kb = self.get_or_create_knowledge_base(persona_handle)
        return kb.add_background(content, source, metadata)

    def retrieve_context(
        self,
        persona_handle: str,
        query: str,
        k: int = 3,
    ) -> str:
        """Retrieve relevant context for a persona based on query.

        Args:
            persona_handle: The unique handle of the persona
            query: The query text (e.g., conversation context)
            k: Number of chunks to retrieve

        Returns:
            Formatted context string from relevant background knowledge
        """
        if persona_handle not in self._knowledge_bases:
            return ""

        kb = self._knowledge_bases[persona_handle]
        documents = kb.retrieve(query, k=k)

        if not documents:
            return ""

        # Format retrieved context
        context_parts = []
        for doc in documents:
            source = doc.metadata.get("source", "background")
            context_parts.append(f"[{source}] {doc.page_content}")

        return "\n---\n".join(context_parts)

    def has_knowledge(self, persona_handle: str) -> bool:
        """Check if a persona has any background knowledge.

        Args:
            persona_handle: The unique handle of the persona

        Returns:
            True if the persona has knowledge in their knowledge base
        """
        if persona_handle not in self._knowledge_bases:
            return False
        kb = self._knowledge_bases[persona_handle]
        return kb._chunk_count > 0

    def clear_persona_knowledge(self, persona_handle: str) -> None:
        """Clear all knowledge for a specific persona.

        Args:
            persona_handle: The unique handle of the persona
        """
        if persona_handle in self._knowledge_bases:
            self._knowledge_bases[persona_handle].clear()

    def clear_all(self) -> None:
        """Clear all knowledge bases."""
        for kb in self._knowledge_bases.values():
            kb.clear()
        self._knowledge_bases.clear()


# Global RAG service instance (can be replaced with dependency injection)
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get the global RAG service instance.

    Returns:
        The RAG service instance
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def set_rag_service(service: Optional[RAGService]) -> None:
    """Set the global RAG service instance.

    This can be used to inject a custom RAG service with different
    embeddings or vector store implementations. Pass None to reset
    the global service (a new default service will be created on
    next get_rag_service() call).

    Args:
        service: The RAG service to use globally, or None to reset
    """
    global _rag_service
    _rag_service = service
