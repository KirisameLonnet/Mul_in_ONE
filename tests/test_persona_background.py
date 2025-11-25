"""Tests for persona background configuration.

Test Timestamp: 2025-11-25
Coverage Scope: Persona background configuration parsing for RAG integration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mul_in_one_nemo.persona import (
    PersonaBackground,
    Persona,
    PersonaSettings,
    load_personas,
)


@pytest.fixture
def temp_yaml_dir():
    """Create a temporary directory for YAML test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestPersonaBackground:
    """Test the PersonaBackground dataclass."""

    def test_default_values(self):
        """Test default values for PersonaBackground."""
        bg = PersonaBackground()
        assert bg.content is None
        assert bg.file is None
        assert bg.source == "background"
        assert bg.rag_enabled is True
        assert bg.rag_top_k == 3

    def test_custom_values(self):
        """Test custom values for PersonaBackground."""
        bg = PersonaBackground(
            content="Some background text",
            file="/path/to/file.txt",
            source="backstory",
            rag_enabled=False,
            rag_top_k=5,
        )
        assert bg.content == "Some background text"
        assert bg.file == "/path/to/file.txt"
        assert bg.source == "backstory"
        assert bg.rag_enabled is False
        assert bg.rag_top_k == 5


class TestPersonaWithBackground:
    """Test Persona with background configuration."""

    def test_persona_without_background(self):
        """Test that persona can be created without background."""
        persona = Persona(
            name="Test Persona",
            handle="test",
            prompt="A test persona",
        )
        assert persona.background is None

    def test_persona_with_background(self):
        """Test that persona can be created with background."""
        bg = PersonaBackground(content="Background story")
        persona = Persona(
            name="Test Persona",
            handle="test",
            prompt="A test persona",
            background=bg,
        )
        assert persona.background is not None
        assert persona.background.content == "Background story"


class TestLoadPersonasWithBackground:
    """Test loading personas with background configuration from YAML."""

    def test_load_persona_with_string_background(self, temp_yaml_dir):
        """Test loading persona with simple string background."""
        yaml_content = """
personas:
  - name: 历史学家
    handle: historian
    prompt: 你是一位历史学家
    background: |
      我是一位专攻中国古代史的学者。
      我在大学里教授历史课程已经有二十年了。
settings:
  max_agents_per_turn: 2
  memory_window: 8
"""
        path = temp_yaml_dir / "test_personas.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        settings = load_personas(path)
        assert len(settings.personas) == 1

        persona = settings.personas[0]
        assert persona.name == "历史学家"
        assert persona.background is not None
        assert "专攻中国古代史" in persona.background.content
        assert persona.background.rag_enabled is True

    def test_load_persona_with_dict_background(self, temp_yaml_dir):
        """Test loading persona with full dict background configuration."""
        yaml_content = """
personas:
  - name: 作曲家
    handle: composer
    prompt: 你是一位作曲家
    background:
      content: |
        我从小就对音乐有着浓厚的兴趣。
        在维也纳音乐学院学习了五年。
      source: life_story
      rag_enabled: true
      rag_top_k: 5
settings:
  max_agents_per_turn: 2
  memory_window: 8
"""
        path = temp_yaml_dir / "test_personas.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        settings = load_personas(path)
        assert len(settings.personas) == 1

        persona = settings.personas[0]
        assert persona.background is not None
        assert persona.background.source == "life_story"
        assert persona.background.rag_enabled is True
        assert persona.background.rag_top_k == 5

    def test_load_persona_with_file_background(self, temp_yaml_dir):
        """Test loading persona with file-based background."""
        yaml_content = """
personas:
  - name: 小说家
    handle: novelist
    prompt: 你是一位小说家
    background:
      file: /path/to/background.txt
      source: biography
      rag_enabled: true
settings:
  max_agents_per_turn: 2
  memory_window: 8
"""
        path = temp_yaml_dir / "test_personas.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        settings = load_personas(path)
        persona = settings.personas[0]

        assert persona.background is not None
        assert persona.background.file == "/path/to/background.txt"
        assert persona.background.source == "biography"

    def test_load_persona_with_rag_disabled(self, temp_yaml_dir):
        """Test loading persona with RAG explicitly disabled."""
        yaml_content = """
personas:
  - name: 简单角色
    handle: simple
    prompt: 一个简单的角色
    background:
      content: Some background
      rag_enabled: false
settings:
  max_agents_per_turn: 2
  memory_window: 8
"""
        path = temp_yaml_dir / "test_personas.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        settings = load_personas(path)
        persona = settings.personas[0]

        assert persona.background is not None
        assert persona.background.rag_enabled is False

    def test_load_multiple_personas_mixed_backgrounds(self, temp_yaml_dir):
        """Test loading multiple personas with different background configs."""
        yaml_content = """
personas:
  - name: 角色A
    handle: role_a
    prompt: 角色A的提示
    # No background
    
  - name: 角色B
    handle: role_b
    prompt: 角色B的提示
    background: 简单的背景文本
    
  - name: 角色C
    handle: role_c
    prompt: 角色C的提示
    background:
      content: 详细的背景配置
      rag_top_k: 10
settings:
  max_agents_per_turn: 3
  memory_window: 10
"""
        path = temp_yaml_dir / "test_personas.yaml"
        path.write_text(yaml_content, encoding="utf-8")

        settings = load_personas(path)
        assert len(settings.personas) == 3

        # Persona A - no background
        assert settings.personas[0].background is None

        # Persona B - string background
        assert settings.personas[1].background is not None
        assert settings.personas[1].background.content == "简单的背景文本"

        # Persona C - dict background
        assert settings.personas[2].background is not None
        assert settings.personas[2].background.rag_top_k == 10
