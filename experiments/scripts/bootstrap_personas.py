import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from utils.api_client import assert_backend_ready, load_api_config
from utils.http_client import build_url, post_json


def load_personas(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("personas 配置需为数组")
    return data


def create_persona(base_url: str, headers: Dict[str, str], persona: Dict[str, Any]) -> Dict[str, Any]:
    url = build_url(base_url, "/api/personas")
    return post_json(url, persona, headers=headers)


def ingest_background(base_url: str, headers: Dict[str, str], persona_id: int, username: str, background: str) -> Dict[str, Any]:
    url = build_url(base_url, f"/api/personas/{persona_id}/ingest_text", query={"username": username})
    payload = {"text": background}
    return post_json(url, payload, headers=headers)


def main():
    parser = argparse.ArgumentParser(description="预置 Personas 并注入后端")
    parser.add_argument("--api-config", type=str, default="config/api_config.json", help="API 配置文件")
    parser.add_argument("--personas", type=str, default="config/personas.json", help="Personas 配置文件")
    args = parser.parse_args()

    api_cfg = load_api_config(Path(args.api_config))
    assert_backend_ready(api_cfg)
    base_url = api_cfg.get("base_url", "http://localhost:8000")
    headers = api_cfg.get("headers") or {}

    personas = load_personas(Path(args.personas))
    created = []
    for persona in personas:
        background = persona.pop("background", None)
        username = persona.get("username")
        res = create_persona(base_url, headers, persona)
        persona_id = res.get("id")
        created.append(res)
        print(f"[OK] created persona id={persona_id}, name={res.get('name')}")
        if background and persona_id and username:
            try:
                ingest_background(base_url, headers, persona_id, username, background)
                print(f"  └─ ingested background for persona id={persona_id}")
            except Exception as e:
                print(f"  └─ ingest failed for persona id={persona_id}: {e}")

    print(f"\n总计创建 {len(created)} 个 persona")


if __name__ == "__main__":
    main()
