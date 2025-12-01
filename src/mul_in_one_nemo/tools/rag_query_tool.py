"""NeMo Agent Toolkit tool: RagQuery.

Allows agents to retrieve background passages for a persona via RAG service.
Read-only; returns passages and basic metadata for citation.

Security: tenant_id and persona_id are injected from config/context at runtime,
not exposed to LLM to prevent token waste and security issues (hallucination risks).
"""

import logging
from typing import List, AsyncGenerator, Optional

from pydantic import BaseModel, Field

from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from mul_in_one_nemo.service.rag_dependencies import get_rag_service
from mul_in_one_nemo.service.rag_context import get_rag_context

logger = logging.getLogger(__name__)


class RagQueryInput(BaseModel):
    """Input schema exposed to LLM - only contains query and top_k.
    
    Security: persona_id and tenant_id are NOT exposed to LLM.
    They are injected from the config/context at runtime.
    """
    query: str = Field(..., description="User/query text to retrieve relevant background")
    top_k: int = Field(default=4, ge=1, le=10, description="Max number of passages to return")


class RagPassage(BaseModel):
    text: str = Field(...)
    source: str | None = Field(default=None)


class RagQueryOutput(BaseModel):
    passages: List[RagPassage] = Field(default_factory=list)


class RagQueryToolConfig(FunctionBaseConfig, name="rag_query_tool"):
    """Configuration for RAG query tool with context injection.
    
    These fields are set at tool registration time or updated during
    session initialization to provide tenant/persona context.
    Note: In multi-tenant scenarios, actual values are injected via
    set_rag_context() at runtime, these are fallbacks only.
    """
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID for multi-tenant isolation (fallback)")
    persona_id: Optional[int] = Field(default=None, description="Persona ID for context scoping (fallback)")


@register_function(config_type=RagQueryToolConfig)
async def rag_query_tool(config: RagQueryToolConfig, builder):
    """RAG query tool with multi-tenant context injection.
    
    Context (tenant_id, persona_id) is provided via config, not from LLM input.
    This ensures:
    1. No token waste asking LLM to provide system metadata
    2. No security risk of LLM hallucinating wrong tenant/persona IDs
    3. Proper tenant isolation at the infrastructure level
    """
    
    async def _single(input_data: RagQueryInput) -> RagQueryOutput:
        try:
            # Always try context first (set by runtime adapter during conversation)
            # This ensures correct tenant_id per request in multi-tenant scenarios
            ctx_tenant, ctx_persona = get_rag_context()
            
            # Fall back to config if context not available (e.g., standalone tool usage)
            tenant_id = ctx_tenant or config.tenant_id
            persona_id = ctx_persona or config.persona_id
            
            if persona_id is None:
                logger.warning("RagQueryTool called without persona_id in config or context")
                return RagQueryOutput(passages=[])
            
            logger.info(
                f"RAG query: tenant={tenant_id}, persona={persona_id}, "
                f"query='{input_data.query[:50]}...', top_k={input_data.top_k}"
            )
            
            rag_service = get_rag_service()
            # Note: retrieve_documents signature now requires tenant_id
            docs = await rag_service.retrieve_documents(
                query=input_data.query,
                persona_id=persona_id,
                tenant_id=tenant_id,
                top_k=input_data.top_k
            )
            
            out = [
                RagPassage(
                    text=getattr(d, "page_content", ""),
                    source=(getattr(d, "metadata", {}) or {}).get("source")
                )
                for d in docs
            ]
            
            logger.info(f"RAG query returned {len(out)} passages")
            return RagQueryOutput(passages=out)
            
        except Exception as e:
            logger.error(f"RagQueryTool failed: {e}", exc_info=True)
            return RagQueryOutput(passages=[])

    async def _stream(input_data: RagQueryInput) -> AsyncGenerator[RagQueryOutput, None]:
        yield await _single(input_data)

    try:
        yield FunctionInfo.create(
            single_fn=_single,
            stream_fn=_stream,
            input_schema=RagQueryInput,
            single_output_schema=RagQueryOutput,
            stream_output_schema=RagQueryOutput,
            description="查询当前 Persona 的背景资料与相关知识片段,用于准确回答涉及人物设定、经历或专业知识的问题。返回最相关的文档片段及来源标注。",
        )
    finally:
        pass
