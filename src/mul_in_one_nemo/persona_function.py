"""Custom function registration for persona replies."""

import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig

# Import Tool Calling Agent components
from nat.agent.tool_calling_agent.agent import ToolCallAgentGraph, ToolCallAgentGraphState

# RAG service singleton accessor
from mul_in_one_nemo.service.rag_dependencies import get_rag_service

logger = logging.getLogger(__name__)


class PersonaDialogueInput(BaseModel):
    """Input schema for persona dialogue function."""
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    user_message: str = Field(default="", description="Latest user message")
    persona_id: Optional[int] = Field(default=None, description="Persona ID used for RAG retrieval context")
    active_participants: Optional[List[str]] = Field(default=None, description="List of active participants in this conversation (handles)")


class PersonaDialogueOutput(BaseModel):
    """Output schema for persona dialogue function."""
    response: str = Field(description="Generated response from persona")


class PersonaDialogueFunctionConfig(FunctionBaseConfig, name="mul_in_one_persona"):
    llm_name: LLMRef = Field(description="LLM provider registered in the builder")
    persona_name: str = Field(default="Persona")
    persona_prompt: str = Field(default="You are an AI persona.")
    instructions: Optional[str] = Field(default=None)
    memory_window: int = Field(default=8)
    tool_names: List[str] = Field(default_factory=list, description="List of tools available to the persona")


@register_function(config_type=PersonaDialogueFunctionConfig)
async def persona_dialogue_function(config: PersonaDialogueFunctionConfig, builder: Builder):
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    # Retrieve and bind tools if any are specified
    tools = []
    if config.tool_names:
        tools = await builder.get_tools(tool_names=config.tool_names, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    
    # Create a simple pass-through prompt for the agent graph
    # The actual system prompt and history will be passed in the state
    agent_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Build the agent graph
    # We set detailed_logs to True to help debugging, or False for production
    graph_builder = ToolCallAgentGraph(
        llm=llm,
        tools=tools,
        prompt=agent_prompt,
        handle_tool_errors=True,
    )
    graph = await graph_builder.build_graph()

    async def _build_messages(input_data: PersonaDialogueInput) -> List[BaseMessage]:
        history = input_data.history
        user_message = input_data.user_message
        persona_id = input_data.persona_id
        active_participants = input_data.active_participants or []

        # Build participant list info
        participants_info = ""
        if active_participants:
            participants_list = "、".join([f"@{p}" for p in active_participants])
            participants_info = f"""【当前会话参与者】
本次对话的参与者有：{participants_list}
⚠️ 重要：你只能 @ 上述列表中的人，不要 @ 不在此列表中的人！

"""

        system_prompt_content = f"""你是{config.persona_name}。{config.persona_prompt}

你正在参与一个多人自由对话。请注意：

{participants_info}【对话规则】
1. 这是自然的群聊对话，不是一问一答。
2. 你可以：
   - 回应其他人的观点（不需要被 @ 也可以回应）
   - 提出自己的问题或想法
   - 对感兴趣的话题发表看法
   - @ 其他人邀请他们参与（格式：@某人，仅限参与者列表中的人）
   - 对某个观点表示赞同或提出不同看法

【何时发言】
✅ 应该发言的情况：
   - 有人 @ 你
   - 话题与你的专长或兴趣相关
   - 你对刚才的观点有独特见解
   - 你想补充或纠正某个信息
   - 对话冷场时可以提出新话题

❌ 不要发言的情况：
   - 别人已经说得很完整了
   - 话题完全不在你的专长范围
   - 你没有新的内容可补充
   - 只是为了发言而发言
   - **用户只说了简单的问候（如"你好"、"晚上好"）时，简短回应即可，不要自己延伸出新话题或提及不存在的上下文**

【发言风格】
- 保持你的个性特点：{config.persona_prompt}
- 自然、真实，像真人在聊天
- 可以简短，不需要每次都长篇大论
- 可以表达情绪和态度
- **根据对话实际内容回复，不要凭空编造或提及对话中没有出现过的事情**

【身份与发言身份】
- 只以你自己的身份发言，绝不假扮他人
- 不要替他人说话或用他人的第一人称回复
- 如果需要引用他人的观点，请用第三人称描述

【重要规则】
1. 如果下文中提供了「检索到的相关资料」，请优先基于这些资料回答，确保回答准确且符合角色设定。
2. 只基于已有的对话历史回复，不要假设或编造对话中未出现的内容。
3. 如果用户只是简单问候，简短回应即可，不要过度延伸。

【可用工具（高优先级）】
- WebSearch：用于检索最新公开信息（新闻、版本、价格等）。当你对事实不确定或用户要求来源时，主动调用该工具，并在回答中引用返回链接。
- RagQuery：用于查询你的人物背景与相关资料。遇到涉及你背景、设定或过往信息的提问或讨论时，优先调用该工具获取片段并据此作答。

工具使用原则：
- 工具调用优先级仅次于系统提示；必要时请主动调用，无需等待用户明确要求。
- 每轮可按需调用 1-2 次，避免过度调用导致延迟。
- 在回答中标注引用，区分来自工具的结论与个人观点。

记住：这是群聊，要像真人一样自然互动！"""

        messages: List[BaseMessage] = [SystemMessage(content=system_prompt_content)]

        if config.instructions:
            messages.append(SystemMessage(content=f"额外指示：{config.instructions}"))

        # 消息优先级：系统提示 > 历史 > 用户消息
        for message in history[-config.memory_window:]:
            speaker = message.get("speaker", "unknown")
            content = message.get("content", "")
            messages.append(HumanMessage(content=f"{speaker}: {content}"))

        if user_message:
            messages.append(HumanMessage(content=f"[用户刚刚说]: {user_message}\n\n现在轮到你发言了。"))
        else:
            messages.append(HumanMessage(content="[基于以上对话，如果你有想法就发言，如果没什么可说的就保持简短或沉默]"))

        return messages

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
        messages = await _build_messages(input_data)
        state = ToolCallAgentGraphState(messages=messages)
        
        try:
            # Invoke the agent graph
            result_state = await graph.ainvoke(state)
            # Extract the final message from the state
            last_message = result_state['messages'][-1]
            return PersonaDialogueOutput(response=_extract_text(last_message))
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in persona dialogue: {error_msg}")
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
        messages = await _build_messages(input_data)
        state = ToolCallAgentGraphState(messages=messages)

        try:
            # Stream the agent graph
            # Note: graph.astream yields state updates or events. 
            # We want to stream the final answer tokens.
            # LangGraph streaming is complex. 
            # For simplicity in this prototype, if tools are used, true streaming of the *final* answer might be tricky 
            # without specifically filtering for the final LLM node's output tokens.
            # NeMo Agent Toolkit's ToolCallAgentGraph might not expose token-level streaming easily via astream(state).
            # However, let's try to fallback to _respond_single if streaming fails or just return the final text.
            
            # Actually, let's check if we can stream the final response. 
            # If we use astream_events, we might get tokens.
            # For now, to ensure it works, we might sacrifice streaming for tool use correctness 
            # OR try to stream but be aware it might just yield the final state.
            
            # Let's try astream and see what we get.
            # If it yields state, we can't "stream" text token by token easily to the frontend unless we use `stream_mode="messages"`.
            
            # If we can't stream properly with tools, we might just await the full response and yield it as one chunk.
            # This is safer to fix the "no response" bug first.
            
            result_state = await graph.ainvoke(state)
            last_message = result_state['messages'][-1]
            text = _extract_text(last_message)
            if text:
                yield PersonaDialogueOutput(response=text)

        except Exception as e:
            error_msg = str(e)
            if "balance is insufficient" in error_msg or "30001" in error_msg:
                yield PersonaDialogueOutput(response="[系统提示] API 账户余额不足，请充值后再试。")
            elif "401" in error_msg or "authentication" in error_msg.lower():
                yield PersonaDialogueOutput(response="[系统提示] API 认证失败，请检查 API Key 配置。")
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                yield PersonaDialogueOutput(response="[系统提示] API 请求频率超限，请稍后再试。")
            else:
                yield PersonaDialogueOutput(response=f"[系统提示] API 调用失败，请检查 API 可用性与配置：{error_msg}")

    return FunctionInfo.create(
        single_fn=_respond_single,
        stream_fn=_respond_stream,
        input_schema=PersonaDialogueInput,
        single_output_schema=PersonaDialogueOutput,
        stream_output_schema=PersonaDialogueOutput,
        description=f"Persona responder for {config.persona_name}"
    )
