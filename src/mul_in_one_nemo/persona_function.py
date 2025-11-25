"""Custom function registration for persona replies."""

from typing import Any, Dict, List, Optional, AsyncGenerator

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

from .rag import get_rag_service


class PersonaDialogueInput(BaseModel):
    """Input schema for persona dialogue function."""
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    user_message: str = Field(default="", description="Latest user message")


class PersonaDialogueOutput(BaseModel):
    """Output schema for persona dialogue function."""
    response: str = Field(description="Generated response from persona")


class PersonaDialogueFunctionConfig(FunctionBaseConfig, name="mul_in_one_persona"):
    llm_name: LLMRef = Field(description="LLM provider registered in the builder")
    persona_name: str = Field(default="Persona")
    persona_handle: str = Field(default="persona")  # Handle for RAG lookup
    persona_prompt: str = Field(default="You are an AI persona.")
    instructions: Optional[str] = Field(default=None)
    memory_window: int = Field(default=8)
    rag_enabled: bool = Field(default=False)  # Whether to use RAG for this persona
    rag_top_k: int = Field(default=3)  # Number of RAG chunks to retrieve


@register_function(config_type=PersonaDialogueFunctionConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def persona_dialogue_function(config: PersonaDialogueFunctionConfig, builder: Builder):
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    def _build_prompts(input_data: PersonaDialogueInput) -> List[HumanMessage | SystemMessage]:
        history = input_data.history
        user_message = input_data.user_message

        # Build RAG context if enabled
        rag_context = ""
        if config.rag_enabled:
            rag_service = get_rag_service()
            if rag_service.has_knowledge(config.persona_handle):
                # Build query from recent conversation context
                query_parts = []
                if user_message:
                    query_parts.append(user_message)
                # Add recent history for better context retrieval
                for msg in history[-3:]:
                    query_parts.append(msg.get("content", ""))
                query = " ".join(query_parts)

                if query.strip():
                    rag_context = rag_service.retrieve_context(
                        config.persona_handle,
                        query,
                        k=config.rag_top_k,
                    )

        # Build system prompt with optional RAG context
        rag_section = ""
        if rag_context:
            rag_section = f"""
【你的背景记忆/经历】
以下是与当前对话相关的你的背景知识和经历，请在回复时自然地运用这些信息：
{rag_context}
---
"""

        system_prompt = f"""你是{config.persona_name}。{config.persona_prompt}
{rag_section}
你正在参与一个多人自由对话。请注意：

【对话规则】
1. 这是自然的群聊对话，不是一问一答。
2. 你可以：
   - 回应其他人的观点（不需要被 @ 也可以回应）
   - 提出自己的问题或想法
   - 对感兴趣的话题发表看法
   - @ 其他人邀请他们参与（格式：@某人）
   - 对某个观点表示赞同或提出不同看法

【何时发言】
✅ 应该发言的情况：
   - 有人 @ 你
   - 话题与你的专长或兴趣相关
   - 你对刚才的观点有独特见解
   - 你想补充或纠正某个信息
   - 对话冷场时可以提出新话题

❌ 不需要发言的情况：
   - 别人已经说得很完整了
   - 话题完全不在你的专长范围
   - 你没有新的内容可补充
   - 只是为了发言而发言

【发言风格】
- 保持你的个性特点：{config.persona_prompt}
- 自然、真实，像真人在聊天
- 可以简短，不需要每次都长篇大论
- 可以表达情绪和态度
- 如果有相关的背景经历，可以自然地提及

记住：这是群聊，要像真人一样自然互动！"""

        prompts: List[HumanMessage | SystemMessage] = [SystemMessage(content=system_prompt)]

        if config.instructions:
            prompts.append(SystemMessage(content=f"额外指示：{config.instructions}"))

        for message in history[-config.memory_window:]:
            speaker = message.get("speaker", "unknown")
            content = message.get("content", "")
            prompts.append(HumanMessage(content=f"{speaker}: {content}"))

        if user_message:
            prompts.append(HumanMessage(content=f"[用户刚刚说]: {user_message}\n\n现在轮到你发言了。"))
        else:
            prompts.append(HumanMessage(content="[基于以上对话，如果你有想法就发言，如果没什么可说的就保持简短或沉默]"))

        return prompts

    def _extract_text(message: Any) -> str:
        content = getattr(message, "content", message)

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "".join(part.get("text", str(part)) if isinstance(part, dict) else str(part) for part in content)

        if hasattr(content, "__str__"):
            return str(content)

        return str(message)

    async def _respond_single(input_data: PersonaDialogueInput) -> PersonaDialogueOutput:
        prompts = _build_prompts(input_data)
        response = await llm.ainvoke(prompts)
        return PersonaDialogueOutput(response=_extract_text(response))

    async def _respond_stream(input_data: PersonaDialogueInput) -> AsyncGenerator[PersonaDialogueOutput, None]:
        prompts = _build_prompts(input_data)

        async for chunk in llm.astream(prompts):
            text = _extract_text(chunk)
            if text:
                yield PersonaDialogueOutput(response=text)

    yield FunctionInfo.create(
        single_fn=_respond_single,
        stream_fn=_respond_stream,
        input_schema=PersonaDialogueInput,
        single_output_schema=PersonaDialogueOutput,
        stream_output_schema=PersonaDialogueOutput,
        description=f"Persona responder for {config.persona_name}"
    )
