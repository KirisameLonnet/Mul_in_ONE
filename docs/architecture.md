# Mul-in-One x NeMo Agent Toolkit 架构概览

Mul-in-One 将 NVIDIA NeMo Agent Toolkit 作为底座，构建一个**自由、多 Agent 互动**的小型演示：
- 多个 persona 通过 LangChain + NeMo NIM LLM 同时在同一 conversation 中回应。
- CLI 负责异步输入、流式输出、用户插入，提升角色扮演体验。

## 关键流程
1. **启动与配置**
   - `.envrc/.envrc.local` 或环境变量导入 NIM API key、默认模型、base_url、Persona/API 配置路径。
   - `Settings.from_env` 读取变量，`load_personas` 解析 `personas/persona.yaml` 与 `personas/api_configuration.yaml`，生成 persona 实例、记忆窗口、默认 proactivity、API 绑定映射。
2. **Runtime 初始**
   - `MultiAgentRuntime` 进入 `async with`，内部创建 `nat.builder.WorkflowBuilder`。
   - 注册统一 `NIMModelConfig`，并在 `persona_dialogue_function` 中通过 `@register_function` 将每个 persona 绑定为 `mul_in_one_persona` Function；Function 负责把系统提示、历史、用户指令交给 LangChain `ChatNVIDIA`，返回 `PersonaDialogueOutput`。
3. **对话控制**
   - CLI `drive` 使用 `ConversationMemory` + `TurnScheduler` + `user_input_queue`：
     - 用户输入通过后台协程推送队列，随时插入对话上下文，但不会中断正在输出的 Agent。
     - `TurnScheduler.next_turn` 以 proactivity、@提及、冷却、连续发言次数、随机扰动等指标计算得分，动态挑选 `max_agents_per_turn` 个 Agent。
     - Agent 通过 `runtime.invoke`（或 `invoke_stream`）生成回复，写回 memory，同时更新 `context_tags`（包括 @ 提及和新用户消息中的关键词）。
     - 支持流式输出，Agent 可逐字输出响应，仍允许用户随时补充新语句。
4. **CLI 展示**
   - `cli.py` 解析 `--stream`、`--message`、`--max-turns` 等参数，展示 `PersonaName> response` 格式。
   - 提示用户：任意时刻输入新消息、使用 @ 提及或退出。

## 模块协作图
```
Env/Settings ─────────────▶ Persona Loader ───────────▶ Runtime (WorkflowBuilder)
          │                           │                            │
          │                           │                            ├──▶ Register LLMs & Functions
          │                           │                            │
          └───▶ CLI/Drive ─────────▶ Scheduler ───────────▶ Runtime.invoke(_stream)
                    ↑                       │
                    │                       └──▶ ConversationMemory (history)
                    │
              user_input_queue
```

## 组件详解
- `Settings`：整合 env、CLI 默认值、persona 路径，生成 `Settings` dataclass（memory_window、max_agents、model、base_url、api_config 路径等）。
- `Persona`：每个 persona 包含 `name`、`handle`、`persona_prompt`、`proactivity`、`api` 绑定等；可在 YAML 中覆盖 temperature、memory_window。
- `ConversationMemory`：slots dataclass 记录 `speaker` 和 `content`，提供 `as_payload` 给 Function（通过 `dataclasses.asdict` 避免 `__dict__` 缺失）。
- `TurnScheduler`：核心算法在 `proactivity` 基础上加入冷却惩罚、连续发言惩罚、被 @ 加分、久未发言加分、随机扰动，兼顾 fairness 与 context-awareness。
- `Runtime.invoke(_stream)`：封装 NAT Function 调用逻辑，`invoke_stream` 允许 Function 产出 chunk（用于流式输出）。
- `PersonaFunction`：系统 Prompt 明确“何时发言/保持沉默”、@ 规范、群聊行为，引导 LLM 生成连贯、个性化文本。

## 运行时体验
- **异步输入**：`asyncio.Queue` + `run_in_executor` 监听用户输入，不阻塞 Agent 输出。
- **流式输出**：`--stream` 模式下逐 chunk 展示 Agent 回复，CLI 同时检查新用户消息并在下一轮加入上下文。
- **用户插入**：新消息写入 memory 和 `context_tags`（包括关键词/ @），`TurnScheduler` 以此影响下一轮发言权重。
- **上下文连续性**：每次请求携带 `history`，LLM 可看到完整回合链条，确保连续讨论。

## 可扩展方向
1. **持久 Memory**：替换 `ConversationMemory` 为 `nat.memory`、Redis 等实现跨进程共享历史。
2. **事件驱动调度**：引入时间、情绪、外部 signal 触发发言。
3. **Guardrails**：在 persona function 中嵌入 Colang 规则/安全策略，强化内容审查。
4. **可观测性**：接入 Phoenix/OTEL/Profiling，追踪 Agent latency、Function 调用、LLM 费用。
