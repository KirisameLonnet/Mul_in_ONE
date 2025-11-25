"""Simple conversation memory store."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import time



@dataclass(slots=True)
class Message:
    speaker: str
    content: str
    recipient: Optional[str] = None  # 支持@或私聊，群聊时为None
    timestamp: float = 0.0           # 消息时间戳，默认0



class ConversationMemory:
    def __init__(self) -> None:
        self._messages: List[Message] = []

    def add(self, speaker: str, content: str, recipient: Optional[str] = None) -> None:
        ts = time.time()
        self._messages.append(Message(speaker=speaker, content=content, recipient=recipient, timestamp=ts))

    def recent(self, limit: int) -> List[Message]:
        return self._messages[-limit:]

    def as_payload(self, limit: int, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """
        返回消息列表，每条包含 speaker, content, recipient, timestamp。
        limit: 默认窗口条数。
        last_n: 若指定则只返回最后 N 条。
        """
        effective_limit = last_n if last_n is not None else limit
        return [asdict(message) for message in self.recent(effective_limit)]

    def get_last_message(self) -> str:
        if not self._messages:
            return ""
        return self._messages[-1].content
