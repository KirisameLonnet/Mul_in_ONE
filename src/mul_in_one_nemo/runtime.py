"""Runtime binding NeMo Agent Toolkit builder with personas."""

from __future__ import annotations

from typing import Dict, Iterable
import logging

from nat.builder.workflow_builder import WorkflowBuilder
from nat.llm.nim_llm import NIMModelConfig
from nat.builder.function import Function

# Import LangChain plugin registrations so the builder knows how to wrap NIM models.
from nat.plugins.langchain import register as _langchain_register  # noqa: F401

from .config import Settings
from .persona import Persona
from .persona_function import PersonaDialogueFunctionConfig
from .tools.web_search_tool import WebSearchToolConfig
from .tools.rag_query_tool import RagQueryToolConfig

logger = logging.getLogger(__name__)

# Monkey-patch ChatNVIDIA to add default timeout
_original_chatnvidia_init = None

def _patch_chatnvidia_init():
    """为 ChatNVIDIA 添加默认 60 秒 timeout"""
    global _original_chatnvidia_init
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        if _original_chatnvidia_init is None:
            _original_chatnvidia_init = ChatNVIDIA.__init__
            
            def patched_init(self, *args, **kwargs):
                # 如果没有设置 timeout，默认 60 秒
                if 'timeout' not in kwargs or kwargs['timeout'] is None:
                    kwargs['timeout'] = 60.0
                    logger.info(f"ChatNVIDIA: setting default timeout=60s")
                return _original_chatnvidia_init(self, *args, **kwargs)
            
            ChatNVIDIA.__init__ = patched_init
            logger.info("Successfully patched ChatNVIDIA with default timeout")
    except ImportError:
        logger.warning("langchain_nvidia_ai_endpoints not available, skipping ChatNVIDIA patch")
    except Exception as e:
        logger.error(f"Failed to patch ChatNVIDIA: {e}")


# Apply patch on module import
_patch_chatnvidia_init()


class MultiAgentRuntime:
    def __init__(self, settings: Settings, personas: Iterable[Persona]):
        self.settings = settings
        self.personas = list(personas)
        self._cm: WorkflowBuilder | None = None
        self.builder: WorkflowBuilder | None = None
        self.default_llm_name = "mul_in_one_nim"
        self.functions: Dict[str, Function] = {}
        self.persona_llms: Dict[str, str] = {}

    async def __aenter__(self) -> "MultiAgentRuntime":
        self._cm = WorkflowBuilder()
        self.builder = await self._cm.__aenter__()
        assert self.builder is not None
        await self._register_llm(self.default_llm_name, self._build_nim_config())
        # Register common tools so the LLM can discover and call them
        await self.builder.add_function(
            "web_search_tool",
            WebSearchToolConfig(),
        )
        await self.builder.add_function(
            "rag_query_tool",
            RagQueryToolConfig(),
        )
        for persona in self.personas:
            llm_name = await self._ensure_persona_llm(persona)
            fn = await self.builder.add_function(
                persona.handle,
                PersonaDialogueFunctionConfig(
                    llm_name=llm_name,
                    persona_name=persona.name,
                    persona_prompt=persona.prompt,
                    instructions=f"语气：{persona.tone}",
                    memory_window=self.settings.memory_window,
                    tool_names=["web_search_tool", "rag_query_tool"],
                ),
            )
            self.functions[persona.name] = fn
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._cm is not None:
            await self._cm.__aexit__(exc_type, exc_val, exc_tb)
        self.builder = None
        self.functions.clear()
        self.persona_llms.clear()

    def _build_nim_config(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
    ) -> NIMModelConfig:
        resolved_key = api_key if api_key is not None else self.settings.nim_api_key
        return NIMModelConfig(
            model_name=model_name or self.settings.nim_model,
            base_url=base_url or self.settings.nim_base_url,
            api_key=resolved_key,
            temperature=temperature if temperature is not None else self.settings.temperature,
        )

    async def _register_llm(self, name: str, config: NIMModelConfig) -> None:
        assert self.builder is not None
        await self.builder.add_llm(name, config)

    async def _ensure_persona_llm(self, persona: Persona) -> str:
        if persona.api is None:
            return self.default_llm_name
        llm_name = f"{persona.handle}_llm"
        if llm_name in self.persona_llms:
            return llm_name
        config = self._build_nim_config(
            model_name=persona.api.model,
            base_url=persona.api.base_url,
            api_key=persona.api.api_key,
            temperature=persona.api.temperature,
        )
        await self._register_llm(llm_name, config)
        self.persona_llms[llm_name] = persona.name
        return llm_name

    async def invoke(self, persona_name: str, payload: dict[str, object]) -> dict[str, str]:
        fn = self.functions[persona_name]
        result = await fn.ainvoke(payload)
        
        # 如果结果是异步生成器（因为底层函数改为了流式），则消费它
        if hasattr(result, '__aiter__'):
            text = ""
            async for chunk in result:
                if hasattr(chunk, 'response'):
                    text += chunk.response
                else:
                    text += str(chunk)
            return text
            
        return result
    
    async def invoke_stream(self, persona_name: str, payload: dict[str, object]):
        """流式调用 persona function"""
        fn = self.functions[persona_name]
        # 尝试使用流式 API
        if hasattr(fn, 'astream'):
            async for chunk in fn.astream(payload):
                if hasattr(chunk, 'response'):
                    yield chunk.response
                else:
                    yield chunk
        else:
            # 降级到非流式
            result = await fn.ainvoke(payload)
            yield result
