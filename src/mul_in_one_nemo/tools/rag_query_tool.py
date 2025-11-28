"""NeMo Agent Toolkit tool: RagQuery.

Allows agents to retrieve background passages for a persona via RAG service.
Read-only; returns passages and basic metadata for citation.
"""

from __future__ import annotations

import logging
from typing import List, AsyncGenerator

from pydantic import BaseModel, Field

from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from mul_in_one_nemo.service.rag_dependencies import get_rag_service

logger = logging.getLogger(__name__)


class RagQueryInput(BaseModel):
    query: str = Field(..., description="User/query text to retrieve relevant background")
    persona_id: int = Field(..., ge=1, description="Persona ID for context scoping")
    top_k: int = Field(default=4, ge=1, le=10, description="Max number of passages to return")


class RagPassage(BaseModel):
    text: str = Field(...)
    source: str | None = Field(default=None)


class RagQueryOutput(BaseModel):
    passages: List[RagPassage] = Field(default_factory=list)


class RagQueryToolConfig(FunctionBaseConfig, name="rag_query_tool"):
    pass


@register_function(config_type=RagQueryToolConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def rag_query_tool(config: RagQueryToolConfig, builder):
    async def _single(input_data: RagQueryInput) -> RagQueryOutput:
        try:
            rag_service = get_rag_service()
            docs = await rag_service.retrieve_documents(input_data.query, input_data.persona_id, top_k=input_data.top_k)
            out = [RagPassage(text=getattr(d, "page_content", ""), source=(getattr(d, "metadata", {}) or {}).get("source")) for d in docs]
            return RagQueryOutput(passages=out)
        except Exception as e:
            logger.error("RagQueryTool failed: %s", e)
            return RagQueryOutput(passages=[])

    async def _stream(input_data: RagQueryInput) -> AsyncGenerator[RagQueryOutput, None]:
        yield await _single(input_data)

    yield FunctionInfo.create(
        single_fn=_single,
        stream_fn=_stream,
        input_schema=RagQueryInput,
        single_output_schema=RagQueryOutput,
        stream_output_schema=RagQueryOutput,
        description="查询当前 Persona 的背景资料与相关知识片段，用于准确回答涉及人物设定、经历或专业知识的问题。返回最相关的文档片段及来源标注。",
    )
