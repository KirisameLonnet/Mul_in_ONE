"""Tests for RAG (Retrieval Augmented Generation) service.

Test Timestamp: 2025-11-25
Coverage Scope: RAG service functionality including embeddings, vector store,
                knowledge base management, and persona integration.
"""

from __future__ import annotations

import pytest

from mul_in_one_nemo.rag import (
    InMemoryVectorStore,
    KnowledgeChunk,
    PersonaKnowledgeBase,
    RAGService,
    SimpleEmbeddings,
    get_rag_service,
    set_rag_service,
)
from langchain_core.documents import Document


class TestSimpleEmbeddings:
    """Test the SimpleEmbeddings fallback implementation."""

    def test_embed_documents(self):
        """Test embedding multiple documents."""
        embeddings = SimpleEmbeddings(dimension=128)
        texts = ["Hello world", "This is a test", "Another document"]
        result = embeddings.embed_documents(texts)

        assert len(result) == 3
        assert all(len(vec) == 128 for vec in result)
        assert all(isinstance(v, float) for vec in result for v in vec)

    def test_embed_query(self):
        """Test embedding a single query."""
        embeddings = SimpleEmbeddings(dimension=256)
        result = embeddings.embed_query("test query")

        assert len(result) == 256
        assert all(isinstance(v, float) for v in result)

    def test_embeddings_are_normalized(self):
        """Test that embeddings are normalized (unit vectors)."""
        embeddings = SimpleEmbeddings(dimension=128)
        result = embeddings.embed_query("Hello world")

        # Check that the embedding is approximately normalized
        magnitude = sum(x * x for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 0.01

    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        embeddings = SimpleEmbeddings(dimension=128)
        vec1 = embeddings.embed_query("Hello world")
        vec2 = embeddings.embed_query("Goodbye moon")

        # Check that they are different
        assert vec1 != vec2


class TestInMemoryVectorStore:
    """Test the in-memory vector store."""

    def test_add_and_retrieve_documents(self):
        """Test adding and retrieving documents."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)

        docs = [
            Document(page_content="The quick brown fox", metadata={"source": "test1"}),
            Document(page_content="Jumped over the lazy dog", metadata={"source": "test2"}),
            Document(page_content="A completely different topic about cooking", metadata={"source": "test3"}),
        ]

        ids = store.add_documents(docs)
        assert len(ids) == 3

        # Search for related documents
        results = store.similarity_search("fox and dog", k=2)
        assert len(results) == 2
        # The fox and dog related documents should be retrieved

    def test_empty_store_returns_empty(self):
        """Test that empty store returns empty results."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)

        results = store.similarity_search("any query", k=5)
        assert results == []

    def test_delete_documents(self):
        """Test deleting documents from the store."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)

        docs = [
            Document(page_content="Document 1", metadata={"chunk_id": "doc1"}),
            Document(page_content="Document 2", metadata={"chunk_id": "doc2"}),
        ]

        ids = store.add_documents(docs)
        assert len(store._documents) == 2

        store.delete(["doc1"])
        assert len(store._documents) == 1
        assert "doc2" in store._documents

    def test_clear_store(self):
        """Test clearing all documents."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)

        docs = [
            Document(page_content="Document 1"),
            Document(page_content="Document 2"),
        ]
        store.add_documents(docs)
        assert len(store._documents) == 2

        store.clear()
        assert len(store._documents) == 0
        assert len(store._vectors) == 0


class TestKnowledgeChunk:
    """Test the KnowledgeChunk dataclass."""

    def test_from_text_creates_chunk(self):
        """Test creating a chunk from text."""
        chunk = KnowledgeChunk.from_text(
            content="Test content",
            source="backstory",
            metadata={"chapter": 1},
        )

        assert chunk.content == "Test content"
        assert chunk.source == "backstory"
        assert chunk.metadata["chapter"] == 1
        assert len(chunk.chunk_id) == 16  # SHA256 truncated

    def test_chunk_ids_are_unique(self):
        """Test that different content produces different chunk IDs."""
        chunk1 = KnowledgeChunk.from_text("Content A", "source1")
        chunk2 = KnowledgeChunk.from_text("Content B", "source1")

        assert chunk1.chunk_id != chunk2.chunk_id


class TestPersonaKnowledgeBase:
    """Test the PersonaKnowledgeBase class."""

    def test_add_and_retrieve_background(self):
        """Test adding and retrieving background knowledge."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)
        kb = PersonaKnowledgeBase(persona_handle="test_persona", vector_store=store)

        background = """
        这是一个测试角色的背景故事。
        
        他出生在一个小镇，从小就对音乐有着浓厚的兴趣。
        
        在学校里，他经常参加音乐比赛，获得了很多奖项。
        
        后来他去了音乐学院深造，专攻钢琴演奏。
        """

        ids = kb.add_background(background, source="backstory")
        assert len(ids) > 0

        # Retrieve relevant context
        results = kb.retrieve("音乐和钢琴", k=2)
        assert len(results) > 0

    def test_clear_knowledge_base(self):
        """Test clearing the knowledge base."""
        embeddings = SimpleEmbeddings()
        store = InMemoryVectorStore(embeddings)
        kb = PersonaKnowledgeBase(persona_handle="test_persona", vector_store=store)

        kb.add_background("Some background content")
        assert kb._chunk_count > 0

        kb.clear()
        assert kb._chunk_count == 0


class TestRAGService:
    """Test the RAGService class."""

    def test_get_or_create_knowledge_base(self):
        """Test getting or creating knowledge bases."""
        service = RAGService()

        kb1 = service.get_or_create_knowledge_base("persona1")
        kb2 = service.get_or_create_knowledge_base("persona1")
        kb3 = service.get_or_create_knowledge_base("persona2")

        # Same handle should return same knowledge base
        assert kb1 is kb2
        # Different handle should return different knowledge base
        assert kb1 is not kb3

    def test_add_persona_background(self):
        """Test adding background knowledge for a persona."""
        service = RAGService()

        ids = service.add_persona_background(
            "historian",
            """
            我是一位历史学家，专攻古代中国历史。
            我在北京大学取得了博士学位，研究方向是秦汉时期的政治制度。
            我发表过多篇关于古代官僚制度的论文。
            """,
            source="academic_background",
        )

        assert len(ids) > 0
        assert service.has_knowledge("historian")
        assert not service.has_knowledge("unknown_persona")

    def test_retrieve_context(self):
        """Test retrieving relevant context."""
        service = RAGService()

        service.add_persona_background(
            "chef",
            """
            我从小就喜欢烹饪，经常帮妈妈在厨房里做饭。
            
            后来我去了法国学习烹饪，在巴黎的一家米其林餐厅工作了五年。
            
            我最擅长的是法式甜点，特别是舒芙蕾和马卡龙。
            
            我还喜欢尝试融合不同菜系，创造新的菜品。
            """,
        )

        # Query about cooking
        context = service.retrieve_context("chef", "你最擅长做什么菜？", k=2)
        assert "烹饪" in context or "甜点" in context or "米其林" in context

    def test_retrieve_empty_for_unknown_persona(self):
        """Test that unknown persona returns empty context."""
        service = RAGService()

        context = service.retrieve_context("unknown", "any query")
        assert context == ""

    def test_clear_persona_knowledge(self):
        """Test clearing knowledge for a specific persona."""
        service = RAGService()

        service.add_persona_background("persona1", "Background 1")
        service.add_persona_background("persona2", "Background 2")

        assert service.has_knowledge("persona1")
        assert service.has_knowledge("persona2")

        service.clear_persona_knowledge("persona1")

        assert not service.has_knowledge("persona1")
        assert service.has_knowledge("persona2")

    def test_clear_all(self):
        """Test clearing all knowledge bases."""
        service = RAGService()

        service.add_persona_background("persona1", "Background 1")
        service.add_persona_background("persona2", "Background 2")

        service.clear_all()

        assert not service.has_knowledge("persona1")
        assert not service.has_knowledge("persona2")


class TestGlobalRAGService:
    """Test the global RAG service instance management."""

    def test_get_rag_service_creates_singleton(self):
        """Test that get_rag_service returns a singleton."""
        # Reset global service
        set_rag_service(None)

        service1 = get_rag_service()
        service2 = get_rag_service()

        assert service1 is service2

    def test_set_rag_service(self):
        """Test setting a custom RAG service."""
        custom_service = RAGService()
        set_rag_service(custom_service)

        retrieved = get_rag_service()
        assert retrieved is custom_service

        # Clean up
        set_rag_service(None)
