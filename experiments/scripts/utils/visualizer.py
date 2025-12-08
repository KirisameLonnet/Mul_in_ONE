from pathlib import Path
import json
from typing import Any, Dict


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_table(title: str, rows: Dict[str, Any]) -> None:
    print(f"\n{title}")
    for name, metrics in rows.items():
        if isinstance(metrics, dict):
            metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
        else:
            metrics_str = str(metrics)
        print(f"  - {name}: {metrics_str}")
