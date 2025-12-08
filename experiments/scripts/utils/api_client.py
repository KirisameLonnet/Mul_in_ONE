import json
import logging
import urllib.request
from pathlib import Path
from typing import Any, Dict

from .http_client import build_url, get_json, post_json

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional
    yaml = None


def load_api_config(path: Path) -> Dict[str, Any]:
    """Load API configuration from JSON or YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"API 配置文件不存在: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("缺少 PyYAML，无法解析 yaml 配置")
        return yaml.safe_load(text)
    return json.loads(text)


def assert_backend_ready(cfg: Dict[str, Any]) -> None:
    """Check if backend is ready by health check endpoint."""
    base_url = cfg.get("base_url", "http://localhost:8000")
    headers = cfg.get("headers") or {}
    health_path = cfg.get("health_path", "/health")
    health_url = build_url(base_url, health_path)
    
    try:
        resp = get_json(health_url, headers=headers, timeout=5)
        logger.info(f"Backend health check passed: {health_url}")
    except Exception as e:
        raise RuntimeError(f"后端健康检查失败: {health_url}, 错误: {e}") from e


class BackendAPIClient:
    """Client for interacting with Mul-in-One backend API."""
    
    def __init__(self, cfg: Dict[str, Any]):
        self.base_url = cfg.get("base_url", "http://localhost:8000")
        self.headers = cfg.get("headers") or {}
        self.timeout = cfg.get("timeouts", {}).get("healthcheck_seconds", 10)
    
    def retrieve_documents(
        self, 
        persona_id: int,
        query: str,
        username: str,
        top_k: int = 4
    ) -> Dict[str, Any]:
        """Call backend RAG retrieval API.
        
        POST /api/personas/{persona_id}/rag/retrieve
        """
        url = build_url(
            self.base_url,
            f"/api/personas/{persona_id}/rag/retrieve",
            {"username": username, "top_k": top_k}
        )
        payload = {"query": query}
        return post_json(url, payload, headers=self.headers, timeout=self.timeout)
    
    def ingest_text(
        self,
        persona_id: int,
        username: str,
        text: str,
        source: str = "experiment"
    ) -> Dict[str, Any]:
        """Call backend RAG ingest API.
        
        POST /api/personas/{persona_id}/ingest_text
        """
        url = build_url(
            self.base_url,
            f"/api/personas/{persona_id}/ingest_text",
            {"username": username}
        )
        payload = {"text": text, "source": source}
        return post_json(url, payload, headers=self.headers, timeout=self.timeout)
    
    def create_session(
        self,
        username: str,
        initial_persona_ids: list = None
    ) -> Dict[str, Any]:
        """Create a conversation session.
        
        POST /api/sessions
        """
        url = build_url(self.base_url, "/api/sessions", {"username": username})
        payload = {"initial_persona_ids": initial_persona_ids or []}
        return post_json(url, payload, headers=self.headers, timeout=self.timeout)
    
    def enqueue_message(
        self,
        session_id: str,
        content: str,
        target_personas: list = None
    ) -> Dict[str, Any]:
        """Send message to session.
        
        POST /api/sessions/{session_id}/messages
        """
        url = build_url(self.base_url, f"/api/sessions/{session_id}/messages")
        payload = {
            "content": content,
            "target_personas": target_personas or []
        }
        return post_json(url, payload, headers=self.headers, timeout=self.timeout)
    
    def list_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List messages from a session.
        
        GET /api/sessions/{session_id}/messages
        """
        url = build_url(
            self.base_url,
            f"/api/sessions/{session_id}/messages",
            {"limit": limit}
        )
        return get_json(url, headers=self.headers, timeout=self.timeout)
    
    def create_persona(
        self,
        username: str,
        name: str,
        prompt: str,
        handle: str = None
    ) -> Dict[str, Any]:
        """Create a new persona.
        
        POST /api/personas
        """
        url = build_url(self.base_url, "/api/personas")
        payload = {
            "username": username,
            "name": name,
            "prompt": prompt,
            "handle": handle or name.lower().replace(" ", "_")
        }
        return post_json(url, payload, headers=self.headers, timeout=self.timeout)
    
    def get_personas(self, username: str) -> Dict[str, Any]:
        """List personas for a user.
        
        GET /api/personas
        """
        url = build_url(self.base_url, "/api/personas", {"username": username})
        return get_json(url, headers=self.headers, timeout=self.timeout)
