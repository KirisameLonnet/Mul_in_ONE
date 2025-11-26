"""Custom function registration for persona replies."""

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

# RAG service singleton accessor
from mul_in_one_nemo.service.rag_dependencies import get_rag_service

logger = logging.getLogger(__name__)


class PersonaDialogueInput(BaseModel):
    """Input schema for persona dialogue function."""
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    user_message: str = Field(default="", description="Latest user message")
    persona_id: Optional[int] = Field(default=None, description="Persona ID used for RAG retrieval context")


class PersonaDialogueOutput(BaseModel):
    """Output schema for persona dialogue function."""
    response: str = Field(description="Generated response from persona")


class PersonaDialogueFunctionConfig(FunctionBaseConfig, name="mul_in_one_persona"):
    llm_name: LLMRef = Field(description="LLM provider registered in the builder")
    persona_name: str = Field(default="Persona")
    persona_prompt: str = Field(default="You are an AI persona.")
    instructions: Optional[str] = Field(default=None)
    memory_window: int = Field(default=8)


@register_function(config_type=PersonaDialogueFunctionConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def persona_dialogue_function(config: PersonaDialogueFunctionConfig, builder: Builder):
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    async def _build_prompts(input_data: PersonaDialogueInput) -> List[HumanMessage | SystemMessage]:
        history = input_data.history
        user_message = input_data.user_message
        persona_id = input_data.persona_id

        system_prompt = f"""你是{config.persona_name}。{config.persona_prompt}

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

【重要】如果下文中提供了「检索到的相关资料」，请优先基于这些资料回答，确保回答准确且符合角色设定。

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

        # RAG: 检索上下文并作为系统提示追加（放在最后，紧贴用户消息）
        if user_message and persona_id is not None:
            try:
                rag_service = get_rag_service()
                docs = await rag_service.retrieve_documents(user_message, persona_id, top_k=4)
                if docs:
                    logger.info(f"RAG retrieved {len(docs)} documents for persona {persona_id}")
                    context_text = "\n\n".join(d.page_content for d in docs)
                    rag_note = (
                        "【检索到的相关资料】\n"
                        f"{context_text}\n\n"
                        "请严格基于以上资料回答用户的问题。这些是关于你自己的真实背景信息，务必准确使用。"
                    )
                    prompts.append(SystemMessage(content=rag_note))
                else:
                    logger.info(f"RAG returned no documents for persona {persona_id}")
            except Exception as e:
                # 记录检索失败日志，继续正常对话
                logger.error(f"RAG retrieval failed for persona {persona_id}: {e}", exc_info=True)

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
        prompts = await _build_prompts(input_data)
        try:
            response = await llm.ainvoke(prompts)
            return PersonaDialogueOutput(response=_extract_text(response))
        except Exception as e:
            error_msg = str(e)
            # 检查是否为余额不足或 API 不可用错误
            if "balance is insufficient" in error_msg or "30001" in error_msg:
                return PersonaDialogueOutput(response="[系统提示] API 账户余额不足，请充值后再试。")
            elif "401" in error_msg or "authentication" in error_msg.lower():
                return PersonaDialogueOutput(response="[系统提示] API 认证失败，请检查 API Key 配置。")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                return PersonaDialogueOutput(response="[系统提示] API 请求频率超限，请稍后再试。")
            else:
                return PersonaDialogueOutput(response=f"[系统提示] API 调用失败，请检查 API 可用性与配置：{error_msg}")

    async def _respond_stream(input_data: PersonaDialogueInput) -> AsyncGenerator[PersonaDialogueOutput, None]:
        prompts = await _build_prompts(input_data)

        try:
            async for chunk in llm.astream(prompts):
                text = _extract_text(chunk)
                if text:
                    yield PersonaDialogueOutput(response=text)
        except Exception as e:
            error_msg = str(e)
            # 检查是否为余额不足或 API 不可用错误
            if "balance is insufficient" in error_msg or "30001" in error_msg:
                yield PersonaDialogueOutput(response="[系统提示] API 账户余额不足，请充值后再试。")
            elif "401" in error_msg or "authentication" in error_msg.lower():
                yield PersonaDialogueOutput(response="[系统提示] API 认证失败，请检查 API Key 配置。")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                yield PersonaDialogueOutput(response="[系统提示] API 请求频率超限，请稍后再试。")
            else:
                yield PersonaDialogueOutput(response=f"[系统提示] API 调用失败，请检查 API 可用性与配置：{error_msg}")

    yield FunctionInfo.create(
        single_fn=_respond_single,
        stream_fn=_respond_stream,
        input_schema=PersonaDialogueInput,
        single_output_schema=PersonaDialogueOutput,
        stream_output_schema=PersonaDialogueOutput,
        description=f"Persona responder for {config.persona_name}"
    )
