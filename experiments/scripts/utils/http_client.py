import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def build_url(base_url: str, path: str, query: Optional[Dict[str, Any]] = None) -> str:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if query:
        qs = urllib.parse.urlencode(query)
        url = f"{url}?{qs}"
    return url


def post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    """POST JSON request and return parsed response."""
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except Exception as e:
        logger.error(f"POST request failed: {url}, error: {e}")
        raise


def get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    """GET JSON request and return parsed response."""
    req_headers = {}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="GET")
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except Exception as e:
        logger.error(f"GET request failed: {url}, error: {e}")
        raise
