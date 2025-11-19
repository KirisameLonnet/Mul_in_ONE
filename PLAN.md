# NeMo Agent Toolkit 集成计划

## 目标
- 以 [NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) 作为基座，构建“1用户-N AI角色”群聊引擎。
- 站在官方多 Agent 编排能力之上：Guardrails、记忆、Scheduler、模态接入等。
- 逐步把 CLI Demo 演进到可部署的微服务。

## 阶段划分
1. **基础环境**
   - 克隆 Toolkit：`git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit.git external/NeMo-Agent-Toolkit`。
   - 使用 `uv` + `.venv` 安装 Toolkit 依赖：`uv pip install -e external/NeMo-Agent-Toolkit[dev]`。
   - 在 `.envrc` 中维护 NeMo API URL/KEY，并为 Toolkit 需要的变量预留位。

2. **最小 CLI Demo**
   - 在 `src/` 重建模块：`agents/`, `session/`, `scheduler/`, 等。
   - 通过 Toolkit 的 Agent/Coordinator API 初始化多个 persona。
   - 利用 Toolkit Guardrails 管理 persona 行为；Memory 由 Toolkit 记忆服务/Redis 驱动。
   - CLI 入口调用 Toolkit Pipeline：`python -m mul_in_one.cli run --rounds 4`。

3. **主动调度与事件驱动**
   - 结合 Toolkit 的 Scheduler/Orchestrator 示例，接入自定义的事件源（用户消息、Webhook、定时器）。
   - 将 proactivity、冷却策略写入 persona 元数据并传给 Toolkit。

4. **NeMo/NIM 推理互通**
   - 使用 Toolkit 内封装好的 NIM/NVIDIA GenAI 接口，以 API KEY + URL 调起推理。
   - 将 Retriever/Memory Manager 组件接入我们的共享上下文池。

5. **测试与文档**
   - 添加 pytest 覆盖：确保 orchestrator、scheduler、persona guardrails 正常。
   - README 更新：安装步骤、NeMo API、Toolkit 克隆方式、示例运行命令。

## 风险点
- Toolkit 自身依赖较多，需确保 `.venv` 不污染系统 Python。
- API KEY 管理需谨慎，默认 `.envrc` 不写入真实值，使用 `.envrc.local`。
- 若后续要部署，需要梳理容器镜像与依赖缓存策略。

## 下一步
1. 初始化仓库结构（pyproject、src、tests、README）。
2. 写 `scripts/bootstrap_toolkit.sh` 自动克隆+安装。
3. 实现 CLI Demo，直接调用 Toolkit 的多 Agent 管线。
