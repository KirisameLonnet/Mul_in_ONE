"""Simple conversation memory store."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass(slots=True)
class Message:
    speaker: str
    content: str


class ConversationMemory:
    def __init__(self) -> None:
        self._messages: List[Message] = []

    def add(self, speaker: str, content: str) -> None:
        self._messages.append(Message(speaker=speaker, content=content))

    def recent(self, limit: int) -> List[Message]:
        return self._messages[-limit:]

    def as_payload(self, limit: int) -> List[Dict[str, str]]:
        return [asdict(message) for message in self.recent(limit)]
