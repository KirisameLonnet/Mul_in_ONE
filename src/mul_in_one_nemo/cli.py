"""Command-line experience for the Mul-in-One demo."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import replace
from typing import Iterable, List, Optional

from .api_config import apply_api_bindings
from .config import Settings
from .memory import ConversationMemory
from .persona import Persona, load_personas
from .runtime import MultiAgentRuntime
from .scheduler import PersonaState, TurnScheduler


# 用于支持用户随时插入消息的全局队列
user_input_queue: Optional[asyncio.Queue] = None
new_user_message: Optional[str] = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mul-in-One NeMo Agent Toolkit demo")
    parser.add_argument("--personas", help="Path to persona YAML file", default=None)
    parser.add_argument("--api-config", help="Path to API configuration YAML", default=None)
    parser.add_argument("--message", help="Send a single user message then exit", default=None)
    parser.add_argument("--max-turns", type=int, default=10, help="Max turns in interactive mode")
    parser.add_argument("--stream", dest="stream", action="store_true", help="Enable streaming output (default)")
    parser.add_argument("--no-stream", dest="stream", action="store_false", help="Disable streaming output")
    parser.set_defaults(stream=True)
    return parser.parse_args()


async def async_input(prompt: str = "") -> str:
    """异步获取用户输入，不阻塞事件循环"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


def build_scheduler(personas: Iterable[Persona], max_agents: int) -> TurnScheduler:
    states = [PersonaState(name=p.name, proactivity=p.proactivity) for p in personas]
    return TurnScheduler(states, max_agents=max_agents)


def extract_tags(user_text: str, personas: Iterable[Persona]) -> List[str]:
    lowered = user_text.lower()
    tags = []
    for persona in personas:
        handle = persona.handle.lower()
        if persona.name.lower() in lowered or handle in lowered:
            tags.append(persona.name)
    return tags


def format_response(persona_name: str, text: str) -> str:
    return f"{persona_name}> {text.strip()}"


async def stream_response(persona_name: str, text_generator) -> str:
    """流式输出响应"""
    print(f"{persona_name}> ", end="", flush=True)
    full_text = ""
    
    try:
        async for chunk in text_generator:
            # 提取文本内容
            if hasattr(chunk, 'content'):
                text = chunk.content
            elif isinstance(chunk, str):
                text = chunk
            else:
                text = str(chunk)
            
            print(text, end="", flush=True)
            full_text += text
        
        print()  # 换行
        return full_text
    except Exception as e:
        print(f"\n[流式输出错误: {e}]")
        return full_text


async def check_user_input() -> Optional[str]:
    """检查用户是否输入了新消息（非阻塞）"""
    global user_input_queue
    
    if user_input_queue is None:
        return None
    
    try:
        return user_input_queue.get_nowait()
    except asyncio.QueueEmpty:
        return None


async def drive(
    runtime: MultiAgentRuntime, 
    scheduler: TurnScheduler, 
    memory: ConversationMemory, 
    initial_user_text: str, 
    memory_window: int,
    max_exchanges: int = 10,  # 增加最大交互轮数
    stream: bool = False
) -> None:
    """
    驱动一次对话流程，支持 Agent 之间的连续对话、用户随时插入消息。
    
    工作流程：
    1. 用户发消息 -> Agent 们响应
    2. Agent A 回复 -> Agent B 可能对 A 的话感兴趣继续回复
    3. 用户随时可以插入新消息，消息会加入上下文，Agent 们继续基于新上下文讨论
    4. 当没有 Agent 想说话时，对话自然结束
    
    Args:
        runtime: 运行时环境
        scheduler: 调度器
        memory: 对话记忆
        initial_user_text: 初始用户输入
        memory_window: 记忆窗口
        max_exchanges: Agent 之间最多交互轮数
        stream: 是否启用流式输出
    """
    global new_user_message
    
    # 记录初始用户消息
    memory.add("用户", initial_user_text)
    context_tags = extract_tags(initial_user_text, runtime.personas)
    
    last_speaker = None
    is_first_round = True
    
    for exchange_round in range(max_exchanges):
        # 在每轮开始前，检查是否有新的用户消息插入
        if new_user_message and not is_first_round:
            user_msg = new_user_message
            new_user_message = None
            print(f"你> {user_msg}")
            memory.add("用户", user_msg)
            # 提取新的 @
            new_tags = extract_tags(user_msg, runtime.personas)
            context_tags.extend(new_tags)
            last_speaker = "用户"
        
        # 决定谁应该发言
        speakers = scheduler.next_turn(
            context_tags=context_tags if exchange_round == 0 else None,
            last_speaker=last_speaker,
            is_user_message=is_first_round
        )
        
        is_first_round = False
        
        # 如果没有人想说话了，对话自然结束
        if not speakers:
            # 再等待一小段时间，看用户是否有新输入
            await asyncio.sleep(0.5)
            if new_user_message:
                continue  # 有新消息，继续循环
            print("[对话暂停，等待新消息...]")
            break
        
        # 每个选中的 Agent 发言
        for persona_name in speakers:
            payload = {
                "history": memory.as_payload(memory_window), 
                "user_message": ""  # 上下文中已包含所有消息
            }
            
            if stream:
                try:
                    result_stream = runtime.invoke_stream(persona_name, payload)
                    reply = await stream_response(persona_name, result_stream)
                except (AttributeError, NotImplementedError):
                    result = await runtime.invoke(persona_name, payload)
                    reply = result.response if hasattr(result, 'response') else str(result)
                    print(format_response(persona_name, reply))
            else:
                result = await runtime.invoke(persona_name, payload)
                reply = result.response if hasattr(result, 'response') else str(result)
                print(format_response(persona_name, reply))
            
            memory.add(persona_name, reply)
            last_speaker = persona_name
            
            # 检查回复中是否有新的 @
            new_tags = extract_tags(reply, runtime.personas)
            context_tags.extend(new_tags)
            
            # Agent 发言完成后，检查是否有用户新消息插入
            # 如果有，不打断，而是在下一轮处理
            await asyncio.sleep(0.1)  # 给一点时间让输入队列更新


async def run(args: argparse.Namespace) -> None:
    global user_input_queue, new_user_message
    
    settings = Settings.from_env(args.personas, args.api_config)
    persona_settings = load_personas(settings.persona_file)
    if settings.api_configuration:
        apply_api_bindings(persona_settings.personas, settings.api_configuration)
    memory_window = persona_settings.memory_window or settings.memory_window
    max_agents = persona_settings.max_agents_per_turn or settings.max_agents_per_turn
    updated = replace(settings, memory_window=memory_window, max_agents_per_turn=max_agents)

    scheduler = build_scheduler(persona_settings.personas, max_agents=max_agents)
    memory = ConversationMemory()

    async with MultiAgentRuntime(updated, persona_settings.personas) as runtime:
        if args.message:
            await drive(runtime, scheduler, memory, args.message, memory_window, stream=args.stream)
            return

        print("=" * 60)
        print("Mul-in-One 多人自由对话系统")
        print("=" * 60)
        print("特性：")
        print("  • Agent 们可以自由对话和互相回应")
        print("  • 你可以随时输入消息加入讨论")
        print("  • 不需要等待，直接输入即可")
        print("  • 输入 'exit' 或 'quit' 退出")
        if args.stream:
            print("  • 流式输出已启用（默认）")
        else:
            print("  • 当前使用非流式输出（通过 --no-stream 关闭）")
        print("=" * 60)
        print()
        
        user_input_queue = asyncio.Queue()
        
        # 启动后台输入监听任务
        async def input_listener():
            """持续监听用户输入"""
            while True:
                try:
                    loop = asyncio.get_event_loop()
                    user_input = await loop.run_in_executor(None, input, "")
                    user_input = user_input.strip()
                    if user_input:
                        await user_input_queue.put(user_input)
                except (KeyboardInterrupt, EOFError):
                    await user_input_queue.put("exit")
                    break
                except Exception as e:
                    print(f"\n[输入监听错误: {e}]")
                    break
        
        input_task = asyncio.create_task(input_listener())
        
        try:
            print("请输入消息开始对话：")
            conversation_task = None
            
            while True:
                # 1. 如果对话正在进行，等待输入或对话结束
                if conversation_task and not conversation_task.done():
                    input_wait_task = asyncio.create_task(user_input_queue.get())
                    
                    done, pending = await asyncio.wait(
                        {conversation_task, input_wait_task},
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    if input_wait_task in done:
                        user_msg = input_wait_task.result()
                        if user_msg.lower() in {"exit", "quit"}:
                            conversation_task.cancel()
                            break
                        
                        # 如果对话刚好也结束了，或者还在运行
                        if conversation_task.done():
                            # 对话已结束，作为新对话开始
                            print(f"你> {user_msg}")
                            conversation_task = asyncio.create_task(
                                drive(
                                    runtime,
                                    scheduler,
                                    memory,
                                    user_msg,
                                    memory_window,
                                    max_exchanges=50,
                                    stream=args.stream
                                )
                            )
                        else:
                            # 对话还在运行，注入消息
                            new_user_message = user_msg
                            # 继续循环，conversation_task 保持不变
                    else:
                        # 对话结束了，输入还没来
                        input_wait_task.cancel()
                        # 继续循环，下一次会进入 else 分支
                        pass
                
                # 2. 如果没有对话在进行（或刚结束）
                else:
                    # 纯粹等待输入
                    user_msg = await user_input_queue.get()
                    
                    if user_msg.lower() in {"exit", "quit"}:
                        break
                    
                    print(f"你> {user_msg}")
                    conversation_task = asyncio.create_task(
                        drive(
                            runtime,
                            scheduler,
                            memory,
                            user_msg,
                            memory_window,
                            max_exchanges=50,
                            stream=args.stream
                        )
                    )
                
        except KeyboardInterrupt:
            print("\n再见！")
        finally:
            input_task.cancel()
            if conversation_task:
                conversation_task.cancel()
            try:
                await input_task
            except asyncio.CancelledError:
                pass


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
