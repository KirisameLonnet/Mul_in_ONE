import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from pydantic import AnyHttpUrl

# Adjust path to import from src
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mul_in_one_nemo.service.rag_service import RAGService # type: ignore


@pytest.fixture
def mock_api_config_path(tmp_path: Path) -> Path:
    """Fixture to create a temporary api_configuration.yaml."""
    config_content = {
        "apis": [
            {
                "name": "TestLLM",
                "base_url": "http://test-llm.com/v1",
                "model": "test-model",
                "api_key": "sk-test-llm-key",
            }
        ],
        "default_api": "TestLLM",
    }
    config_file = tmp_path / "api_configuration.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config_content, f)
    return config_file

@pytest.fixture
def mock_milvus_vector_store():
    """Mocks the Milvus vector store."""
    with patch("mul_in_one_nemo.service.rag_service.Milvus") as mock_milvus_cls:
        mock_milvus_instance = AsyncMock() # Use AsyncMock for the instance
        mock_milvus_instance.aadd_documents.return_value = ["mock_doc_id_1"]
        mock_milvus_cls.return_value = mock_milvus_instance # Set the return value for the constructor
        yield mock_milvus_instance

@pytest.fixture
def rag_service_instance(mock_api_config_path: Path) -> RAGService:
    """Fixture to provide an RAGService instance with a mocked config path."""
    return RAGService(config_path=mock_api_config_path)


@pytest.mark.asyncio
async def test_ingest_url_success(
    rag_service_instance: RAGService,
    mock_milvus_vector_store: AsyncMock,
    tmp_path: Path,
):
    """Test successful URL ingestion."""
    test_url = AnyHttpUrl("http://example.com")
    persona_id = 123
    
    with patch("mul_in_one_nemo.service.rag_service.scrape") as mock_scrape, \
         patch("mul_in_one_nemo.service.rag_service.OpenAIEmbeddings.aembed_documents") as mock_aembed: # Changed patch target
        mock_scrape.return_value = ([{"url": str(test_url), "html": "<html><body><h1>Test Title</h1><p>Test content.</p></body></html>"}], [])
        mock_aembed.return_value = [[0.1] * 1536] # Dummy embedding for one chunk

        # Ensure CACHE_BASE_PATH is temporary
        with patch("mul_in_one_nemo.service.rag_service.CACHE_BASE_PATH", str(tmp_path / "rag_cache")):
            result = await rag_service_instance.ingest_url(test_url, persona_id)

            assert result["status"] == "success"
            assert result["documents_added"] == 1 # Changed from 2 to 1
            assert result["collection_name"] == f"persona_{persona_id}_rag"

            mock_scrape.assert_called_once_with([str(test_url)])
            mock_aembed.assert_called_once() # Verify embedder was called
            mock_milvus_vector_store.aadd_documents.assert_called_once()
            # Verify cache file is removed
            cache_dir = tmp_path / "rag_cache" / "example.com"
            assert not list(cache_dir.iterdir()) # check if directory is empty


@pytest.mark.asyncio
async def test_ingest_url_scrape_failure(
    rag_service_instance: RAGService,
    mock_milvus_vector_store: AsyncMock,
    tmp_path: Path,
):
    """Test URL ingestion failure due to scraping error."""
    test_url = AnyHttpUrl("http://fail.com")
    persona_id = 456

    with patch("mul_in_one_nemo.service.rag_service.scrape") as mock_scrape, \
         patch("mul_in_one_nemo.service.rag_service.OpenAIEmbeddings.aembed_documents") as mock_aembed: # Changed patch target
        mock_scrape.return_value = ([], [{"url": str(test_url), "error": "mock network error"}])
        
        with pytest.raises(RuntimeError, match="Failed to scrape URL"):
            await rag_service_instance.ingest_url(test_url, persona_id)
        
        mock_scrape.assert_called_once_with([str(test_url)])
        mock_aembed.assert_not_called() # Embedder should not be called on scrape failure
        mock_milvus_vector_store.aadd_documents.assert_not_called()

