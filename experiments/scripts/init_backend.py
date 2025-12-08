#!/usr/bin/env python3
"""
Backend initialization script for Mul-in-One experiments.

Creates test user, API profiles, personas, and ingests sample documents.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class BackendInitializer:
    """Initialize backend with test data."""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.username = "eval_user"
        self.user_email = "eval_user@test.com"
        self.user_password = "testpass123"
        self.display_name = "Eval User"
        self.persona_id: Optional[int] = None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to backend."""
        url = f"{self.backend_url}{endpoint}"
        
        try:
            if data:
                body = json.dumps(data).encode('utf-8')
            else:
                body = None
            
            req = Request(
                url,
                data=body,
                method=method,
                headers={'Content-Type': 'application/json'}
            )
            
            with urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data
        except HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
                error_data = json.loads(error_body)
                raise Exception(f"HTTP {e.code}: {error_data}") from e
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {error_body}") from e
        except URLError as e:
            logger.error(f"Request to {url} failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response from {url}: {e}")
            raise
    
    def check_backend(self) -> bool:
        """Check if backend is running."""
        try:
            self._make_request("GET", f"/api/personas?username={self.username}")
            logger.info("Backend is running and accessible")
            return True
        except Exception as e:
            logger.error(f"Backend check failed: {e}")
            logger.error(f"Make sure backend is running at {self.backend_url}")
            return False
    
    def create_user(self) -> bool:
        """Create test user."""
        try:
            logger.info(f"Creating user: {self.username}")
            response = self._make_request(
                "POST",
                "/api/auth/register",
                {
                    "email": self.user_email,
                    "password": self.user_password,
                    "username": self.username,
                    "display_name": self.display_name
                }
            )
            
            if "id" in response:
                logger.info(f"User created successfully: {self.username} (ID: {response['id']})")
                return True
            else:
                logger.error(f"Failed to create user: {response}")
                return False
        except Exception as e:
            error_str = str(e)
            if "REGISTER_USER_ALREADY_EXISTS" in error_str or "already exists" in error_str.lower():
                logger.warning(f"User already exists: {self.username}")
                return True
            logger.error(f"User creation failed: {e}")
            return False
    
    def create_api_profiles(self) -> bool:
        """Create LLM and embedding API profiles."""
        success = True
        
        # Load API keys from config if available
        config_path = Path(__file__).parent.parent / "config" / "api_config.json"
        embedding_api_key = ""  # Set via environment variable or API config
        llm_api_key = ""  # Set via environment variable or API config
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    if "embedding" in config and "api_key" in config["embedding"]:
                        embedding_api_key = config["embedding"]["api_key"]
                    if "llm" in config and "api_key" in config["llm"]:
                        llm_api_key = config["llm"]["api_key"]
            except Exception as e:
                logger.warning(f"Failed to load API keys from config: {e}")
        
        # Create embedding profile
        try:
            logger.info("Creating embedding API profile...")
            response = self._make_request(
                "POST",
                "/api/api-profiles",
                {
                    "username": self.username,
                    "name": "Google Embedding",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "model": "text-embedding-004",
                    "api_key": embedding_api_key,
                    "is_embedding_model": True,
                    "embedding_dim": 768
                }
            )
            
            if "id" in response:
                logger.info(f"Embedding profile created: ID {response['id']}")
            else:
                logger.warning(f"Embedding profile creation may have failed: {response}")
                success = False
        except Exception as e:
            logger.error(f"Failed to create embedding profile: {e}")
            success = False
        
        # Create LLM profile
        try:
            logger.info("Creating LLM API profile...")
            response = self._make_request(
                "POST",
                "/api/api-profiles",
                {
                    "username": self.username,
                    "name": "SiliconFlow LLM",
                    "base_url": "https://api.siliconflow.cn/v1",
                    "model": "deepseek-ai/DeepSeek-V3.2",
                    "api_key": llm_api_key,
                    "is_embedding_model": False,
                    "temperature": 0.3
                }
            )
            
            if "id" in response:
                logger.info(f"LLM profile created: ID {response['id']}")
            else:
                logger.warning(f"LLM profile creation may have failed: {response}")
                success = False
        except Exception as e:
            logger.error(f"Failed to create LLM profile: {e}")
            success = False
        
        return success
    
    def create_persona(self) -> bool:
        """Create test persona."""
        try:
            logger.info("Creating test persona...")
            response = self._make_request(
                "POST",
                "/api/personas",
                {
                    "username": self.username,
                    "name": "Test Persona",
                    "prompt": "You are a helpful assistant for testing RAG capabilities.",
                    "background": "This is a test persona created for experiment evaluation. "
                                 "It has access to a knowledge base for RAG retrieval."
                }
            )
            
            if "id" in response:
                self.persona_id = response["id"]
                logger.info(f"Persona created successfully: ID {self.persona_id}")
                return True
            else:
                logger.error(f"Failed to create persona: {response}")
                return False
        except Exception as e:
            logger.error(f"Persona creation failed: {e}")
            return False
    
    def ingest_sample_documents(self) -> bool:
        """Ingest sample documents for RAG."""
        if not self.persona_id:
            logger.error("Persona ID not set, skipping document ingestion")
            return False
        
        documents = [
            "Machine learning is a subset of artificial intelligence that enables systems to "
            "learn and improve from experience without being explicitly programmed. It focuses "
            "on developing computer programs that can access data and use it to learn for themselves.",
            
            "Natural language processing (NLP) is a subfield of linguistics, computer science, and "
            "artificial intelligence concerned with the interactions between computers and human language. "
            "NLP is used to apply machine learning algorithms to text and speech.",
            
            "Deep learning is part of a broader family of machine learning methods based on artificial "
            "neural networks with representation learning. Learning can be supervised, semi-supervised or unsupervised."
        ]
        
        all_success = True
        
        for i, doc in enumerate(documents, 1):
            try:
                logger.info(f"Ingesting document {i}/{len(documents)}...")
                response = self._make_request(
                    "POST",
                    f"/api/personas/{self.persona_id}/ingest_text?username={self.username}",
                    {"text": doc}
                )
                
                if response.get("status") == "success":
                    logger.info(f"Document {i} ingested: {response.get('documents_added', 1)} chunks added")
                else:
                    logger.warning(f"Document {i} ingestion may have failed: {response}")
                    all_success = False
            except Exception as e:
                logger.error(f"Failed to ingest document {i}: {e}")
                all_success = False
        
        return all_success
    
    def initialize(self) -> bool:
        """Run full initialization sequence."""
        logger.info("=" * 50)
        logger.info("Backend Initialization")
        logger.info("=" * 50)
        logger.info("")
        
        # Check backend
        if not self.check_backend():
            return False
        
        logger.info("")
        
        # Create user
        if not self.create_user():
            logger.error("Failed to create user, aborting")
            return False
        
        logger.info("")
        
        # Create API profiles
        if not self.create_api_profiles():
            logger.warning("Some API profiles failed to create, continuing...")
        
        logger.info("")
        
        # Create persona
        if not self.create_persona():
            logger.error("Failed to create persona, aborting")
            return False
        
        logger.info("")
        
        # Ingest documents
        if not self.ingest_sample_documents():
            logger.warning("Some documents failed to ingest, continuing...")
        
        logger.info("")
        logger.info("=" * 50)
        logger.info("Initialization Complete!")
        logger.info("=" * 50)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  Backend URL: {self.backend_url}")
        logger.info(f"  Test user: {self.username}")
        logger.info(f"  Persona ID: {self.persona_id}")
        logger.info("")
        logger.info("You can now run experiments:")
        logger.info("  cd experiments/scripts")
        logger.info("  uv run exp1_rag_evaluation.py --seed 42")
        logger.info("")
        
        return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Initialize Mul-in-One backend with test data"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    initializer = BackendInitializer(backend_url=args.backend_url)
    success = initializer.initialize()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
