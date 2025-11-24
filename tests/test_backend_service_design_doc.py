"""Tests for backend_service_design.md structure.

Test Timestamp: 2025-11-20T16:15:00+08:00
Coverage Scope: docs/backend_service_design.md sections, payload samples, and testing strategy notes.
"""

from __future__ import annotations

import pathlib

import pytest

DOC_PATH = pathlib.Path(__file__).resolve().parent.parent / "docs" / "backend_service_design.md"

REQUIRED_SECTIONS = [
    "## 1. 设计目标",
    "## 2. 服务分层",
    "## 3. 请求生命周期",
    "## 4. API 概要",
    "## 5. 数据模型",
    "## 6. Runtime & Scheduler 策略",
    "## 7. 配置与依赖",
    "## 8. 可观测性",
    "## 9. 迭代里程碑",
    "## 10. 进度记录",
    "## 11. 开放问题",
    "## 12. 模块接口速览",
    "## 13. 测试策略",
]

REQUIRED_KEYWORDS = [
    "RuntimeSession",
    "asyncio.Queue",
    "sticky session",
    "POST /api/sessions/{id}/messages",
    "ws_token",
]


@pytest.mark.docs
def test_design_doc_contains_required_sections():
    text = DOC_PATH.read_text(encoding="utf-8")
    positions = []
    for section in REQUIRED_SECTIONS:
        assert section in text, f"Missing section: {section}"
        positions.append(text.index(section))
    assert positions == sorted(positions), "Sections are out of order"


@pytest.mark.docs
def test_design_doc_captures_key_keywords():
    text = DOC_PATH.read_text(encoding="utf-8")
    for keyword in REQUIRED_KEYWORDS:
        assert keyword in text, f"Missing keyword context: {keyword}"