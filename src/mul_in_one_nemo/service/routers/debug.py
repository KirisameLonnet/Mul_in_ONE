from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/debug", tags=["debug"])

LOG_FILE_RELATIVE = os.path.join("logs", "backend.log")


def _read_tail_lines(file_path: str, max_lines: int) -> List[str]:
    if not os.path.exists(file_path):
        return ["<log file not found>"]
    lines: List[str] = []
    try:
        with open(file_path, "rb") as f:
            # Efficient tail read
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            block_size = 1024
            buffer = b""
            while pos > 0 and len(lines) <= max_lines:
                read_size = block_size if pos >= block_size else pos
                pos -= read_size
                f.seek(pos)
                buffer = f.read(read_size) + buffer
                while b"\n" in buffer:
                    idx = buffer.index(b"\n")
                    line = buffer[:idx]
                    buffer = buffer[idx + 1 :]
                    lines.append(line.decode(errors="replace"))
            if buffer:
                lines.append(buffer.decode(errors="replace"))
    except Exception as e:
        return [f"<error reading log file: {e}>"]
    # Return only the last max_lines, in chronological order
    return lines[-max_lines:]


@router.get("/logs")
async def get_logs(lines: int = Query(default=500, ge=1, le=5000)):
    """
    Return the last N lines from the backend log file.
    """
    log_path = os.path.join(os.getcwd(), LOG_FILE_RELATIVE)
    tail = _read_tail_lines(log_path, lines)
    return {"path": LOG_FILE_RELATIVE, "lines": tail, "count": len(tail)}
