import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_qa_dataset(path: Path) -> List[Dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("QA dataset must be a list")
    return data


def load_conversations(path: Path) -> List[List[Dict[str, Any]]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("Conversations dataset must be a list of dialogs")
    return data


def build_retrieval_index(docs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {doc["id"]: doc for doc in docs}


def mock_retrieve(query: str, index: Dict[str, Dict[str, Any]], top_k: int) -> List[str]:
    """Deterministic pseudo retrieval: rank by simple hash to avoid external calls."""
    doc_ids = list(index.keys())
    scored: List[Tuple[int, str]] = []
    for doc_id in doc_ids:
        score = hash(query + doc_id) % 1000
        scored.append((score, doc_id))
    scored.sort(reverse=True)
    return [doc_id for _, doc_id in scored[:top_k]]
