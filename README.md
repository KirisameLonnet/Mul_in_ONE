# Mul-in-One - 多人自由对话系统

基于 NVIDIA NeMo Agent Toolkit 构建的**多智能体自由对话系统**，实现多个 AI Agent 之间的自然群聊互动。

## ✨ 核心特性

### 🗣️ 自然多人对话
- **Agent 自由互动**：Agent 之间可以自由对话，无需严格轮流
- **智能决策发言**：基于话题兴趣、主动性和上下文动态决定谁该说话
- **避免霸占对话**：连续发言惩罚机制，确保对话公平性
- **冷场自动激活**：检测对话冷场，自动激活沉默的 Agent

### 👤 用户随时插入
- **无缝加入讨论**：用户可以在 Agent 对话过程中随时插入新消息
- **上下文连续**：新消息自动融入对话上下文，Agent 们基于新信息继续讨论
- **不打断输出**：等待当前 Agent 说完，再处理用户新消息

### 🎭 灵活的 Persona 系统
- **YAML 配置**：通过 YAML 定义 Agent 的性格、语气、专长
- **个性化 API**：每个 Persona 可以绑定不同的 LLM 模型和参数
- **主动性控制**：调节每个 Agent 的活跃度和发言频率
- **记忆窗口**：可配置的对话历史记忆

### 🚀 高级功能
- **流式输出**（可选）：逐字显示 Agent 回复，更自然的对话体验
- **@ 提及系统**：Agent 可以 @ 其他人，被 @ 者优先回应
- **异步架构**：后台监听用户输入，不阻塞对话流程
- **多 API 支持**：支持配置多个 LLM 提供商（OpenAI 兼容 API）

## 🏗️ 项目架构

```
src/mul_in_one_nemo/
├── config.py           # 配置管理，环境变量与 YAML 配置
├── persona.py          # Persona 定义与加载
├── scheduler.py        # 动态对话调度器（核心算法）
├── memory.py           # 共享对话记忆
├── runtime.py          # NeMo Runtime 封装
├── persona_function.py # Persona 对话函数（与 NeMo 集成）
├── cli.py              # 命令行界面（支持异步输入）
└── api_config.py       # API 配置管理

personas/
├── persona.yaml        # Persona 定义（角色、性格、专长）
└── api_configuration.yaml  # API 配置（模型、URL、密钥）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd Mul_in_ONE

# 使用 uv 创建虚拟环境
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 克隆 NeMo Agent Toolkit
mkdir -p external
git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit.git external/NeMo-Agent-Toolkit

# 安装依赖
uv pip install -e external/NeMo-Agent-Toolkit[langchain]
uv pip install -e .[dev]
```

### 2. 配置 API

编辑 `personas/api_configuration.yaml`：

```yaml
apis:
  - name: Qwen32B
    base_url: https://api.siliconflow.cn/v1  # 或其他 OpenAI 兼容 API
    model: Qwen/Qwen3-32B
    api_key: sk-xxxxx  # 你的 API Key
    temperature: 0.7

default_api: Qwen32B

persona_bindings:
  - persona: 温柔女仆
    api: Qwen32B
```

**支持的 API 提供商**：
- SiliconFlow
- OpenAI
- NVIDIA NIM
- 任何 OpenAI 兼容的 API

### 3. 配置 Persona

编辑 `personas/persona.yaml`：

```yaml
personas:
  - name: 技术专家
    handle: tech_expert
    persona_prompt: "你是一个技术专家，对 AI、编程和科技有深入见解"
    proactivity: 0.7  # 主动性 (0.0-1.0)
    
  - name: 温柔女仆
    handle: maid
    persona_prompt: "你是一个温柔体贴的女仆，说话温柔礼貌"
    proactivity: 0.5

memory_window: 8  # 记忆窗口（保留最近 8 条消息）
max_agents_per_turn: 2  # 每轮最多 2 个 Agent 发言
```

### 4. 运行

```bash
# 基础模式
uv run mul-in-one-nemo

# 启用流式输出（推荐）
uv run mul-in-one-nemo --stream

# 单次消息模式
uv run mul-in-one-nemo --message "大家讨论一下 AI 的未来"
```

## 💡 使用示例

### 场景1：多人讨论

```
你> 大家觉得 AI 会取代人类的工作吗？

技术专家> 这是个复杂的问题。AI 确实会改变很多行业，但不是简单的"取代"...

温柔女仆> 主人，我觉得技术专家说得有道理呢。AI 更像是工具，可以帮助人类...

[继续对话...]
```

### 场景2：随时插入

```
技术专家> 从技术角度看，AI 的发展主要依赖于...

温柔女仆> 确实，而且我注意到最近...

你> 等等，我想问一个问题，关于 AI 安全...

温柔女仆> ...的数据质量提升。

技术专家> 关于主人刚才提到的 AI 安全问题，这确实很重要...
```

### 场景3：@ 提及

```
你> @技术专家 你能详细解释一下大语言模型的原理吗？

技术专家> 当然！大语言模型基于 Transformer 架构...

温柔女仆> @技术专家 这个解释真棒！我想补充一点...
```

## 📊 调度算法

系统使用**动态评分机制**决定 Agent 发言：

```python
基础分数 = 主动性 (proactivity)

加分项：
+ 被 @ 提及：+100 (必选)
+ 很久没说话：+0.05 * 轮次间隔
+ 回应上一个发言者：+0.15
+ 用户新消息且高主动性：+0.2
+ 随机性：±0.1

减分项：
- 冷却期内：-0.6
- 连续发言：-0.3 * 连续次数
```

## 🛠️ 高级配置

### 环境变量

```bash
# 默认 API 配置
export MUL_IN_ONE_NIM_MODEL="meta/llama-3.1-70b-instruct"
export MUL_IN_ONE_NIM_BASE_URL="https://integrate.api.nvidia.com/v1"
export MUL_IN_ONE_NEMO_API_KEY="<your-key>"

# 或使用
export NVIDIA_API_KEY="<your-key>"

# Persona 和 API 配置文件路径
export MUL_IN_ONE_PERSONAS="personas/persona.yaml"
export MUL_IN_ONE_API_CONFIG="personas/api_configuration.yaml"
```

### CLI 参数

```bash
mul-in-one-nemo [options]

选项：
  --personas PATH       Persona 配置文件路径
  --api-config PATH     API 配置文件路径
  --message TEXT        单次消息模式
  --max-turns N         最大对话轮数 (默认: 10)
  --stream              启用流式输出
  -h, --help            显示帮助
```

## 🧪 测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试
python -m pytest tests/test_scheduler.py
python -m pytest tests/test_persona_loader.py
```

## 📖 文档

- `docs/architecture.md` - 系统架构设计
- `docs/persona_spec.md` - Persona 规范文档
- `PLAN.md` - 项目规划与进度

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 NVIDIA NeMo Agent Toolkit 构建，遵循相应的开源协议。

## 🙏 致谢

- [NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit)
- LangChain
- SiliconFlow (示例 API 提供商)

---

**享受多人 AI 对话的乐趣！** 🎉
