# Mul-in-One 实验程序

三个核心实验，评估 RAG 检索质量、多智能体调度、以及 Tool-First 架构的性能。

## 快速开始

### 前置：启动后端

在项目根目录启动后端服务：

```bash
cd /path/to/Mul_in_ONE
./scripts/start_backend.sh
```

### 初始化数据

在 experiments 目录初始化测试数据：

```bash
cd experiments
./scripts/init_backend.py
```

### 运行所有实验

```bash
cd experiments
./run_all_experiments.sh [--seed 42]
```

### 运行单个实验

```bash
cd experiments/scripts

# 实验 1: RAG 检索质量
uv run exp1_rag_evaluation.py --seed 42 --persona-id 1 --username eval_user

# 实验 2: 多智能体调度
uv run exp2_scheduler_eval.py --seed 42 --persona-id 1 --username eval_user

# 实验 3: Tool-First 对比
uv run exp3_tool_first_compare.py --seed 42 --persona-id 1 --username eval_user
```

## 项目结构

```
experiments/
├── README.md                     # 本文件
├── scripts/                      # 实验脚本
│   ├── exp1_rag_evaluation.py    # RAG 质量评估
│   ├── exp2_scheduler_eval.py    # 调度器评估
│   ├── exp3_tool_first_compare.py # Tool-First 对比
│   ├── init_backend.py           # 后端初始化工具（Python）
│   ├── init_backend.sh           # 后端初始化脚本（Bash 包装）
│   └── utils/
│       ├── api_client.py         # 后端 API 客户端
│       ├── http_client.py        # HTTP 工具函数
│       ├── data_loader.py        # 数据集加载
│       └── metrics.py            # 评估指标计算
├── config/                       # 实验配置文件
│   ├── api_config.json           # 后端 API 和外部服务配置
│   ├── rag_eval_config.json      # 实验 1 配置
│   ├── scheduler_config.json     # 实验 2 配置
│   └── tool_first_config.json    # 实验 3 配置
├── datasets/                     # 实验数据集
│   ├── product_qa.json           # RAG 问答数据（实验 1）
│   ├── conversations.json        # 多轮对话数据（实验 2）
│   └── comparison_qa.json        # 对比测试数据（实验 3）
└── results/                      # 实验结果
    ├── exp1_results.json         # 实验 1 结果
    ├── exp2_results.json         # 实验 2 结果
    ├── exp3_results.json         # 实验 3 结果
    └── figures/                  # 图表输出
```

## 三个核心实验

### 实验 1: RAG 检索质量评估 (exp1_rag_evaluation.py)

**目标**：评估 RAG 系统的检索准确性和质量

**指标**：
- Recall@K (K=1,3,5)
- MRR (Mean Reciprocal Rank)
- nDCG@K (Normalized Discounted Cumulative Gain)

**配置文件**：`config/rag_eval_config.json`
- `dataset.qa_file`：问答数据文件路径
- `dataset.top_k_values`：评估的 top-k 值列表
- `output_path`：结果输出路径

**输出**：`results/exp1_results.json`
- 每个 top-k 值的检索指标
- 总结统计

**运行**：
```bash
cd scripts
uv run exp1_rag_evaluation.py --seed 42 --persona-id 1 --username eval_user
```

### 实验 2: 多智能体调度评估 (exp2_scheduler_eval.py)

**目标**：评估多个智能体的协作和调度效果

**指标**：
- 发言分布（基尼系数）
- 参与率
- 平均响应延迟
- 会话完成率

**配置文件**：`config/scheduler_config.json`
- `dataset.conversation_file`：对话数据文件路径
- `output_path`：结果输出路径

**输出**：`results/exp2_results.json`
- 调度指标统计
- 发言分布分析

**运行**：
```bash
cd scripts
uv run exp2_scheduler_eval.py --seed 42 --persona-id 1 --username eval_user
```

### 实验 3: Tool-First 架构对比 (exp3_tool_first_compare.py)

**目标**：对比 Baseline（预注入所有文档）vs Tool-First（按需检索）的效率差异

**指标**：
- Token 成本对比
- 延迟对比（p50, p95）
- 精度对比

**配置文件**：`config/tool_first_config.json`
- `baseline.top_k`：Baseline 模式的预注入文档数
- `output_path`：结果输出路径

**输出**：`results/exp3_results.json`
- Baseline vs Tool-First 的指标对比
- 效率提升分析

**运行**：
```bash
cd scripts
uv run exp3_tool_first_compare.py --seed 42 --persona-id 1 --username eval_user
```

## 配置说明

### api_config.json

系统全局配置，包括：

```json
{
  "base_url": "http://localhost:8000",          # 后端 API 地址
  "postgres": {
    "dsn": "postgresql+asyncpg://..."           # 数据库连接
  },
  "milvus": {
    "host": "localhost",
    "port": 19530
  },
  "llm": {                                       # LLM API 配置
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "deepseek-ai/DeepSeek-V3.2",
    "api_key": "..."
  },
  "embedding": {                                 # Embedding API 配置
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "model": "text-embedding-004",
    "api_key": "...",
    "dim": 768
  }
}
```

### 实验特定配置

每个实验有自己的配置文件，只包含关键参数（其他由后端自动处理）。

## 后端初始化

需要创建测试用户和 Persona 才能运行实验。使用提供的脚本：

```bash
# Python 版（推荐，更可靠）
python3 scripts/init_backend.py --backend-url http://localhost:8000

# 或 Bash 版（包装器）
./scripts/init_backend.sh
```

初始化会自动创建：
- 用户：`eval_user`
- Persona：ID 1
- API 配置：Google Embedding + SiliconFlow LLM
- 示例文档：3 个 ML 相关文档

## API 客户端

脚本通过 `BackendAPIClient` 调用后端 API：

```python
from utils.api_client import BackendAPIClient

client = BackendAPIClient(config)

# 摄取文本
client.ingest_text(persona_id=1, username="eval_user", text="...")

# 检索文档
docs = client.retrieve_documents(
    persona_id=1, 
    username="eval_user",
    query="...",
    top_k=5
)

# 创建会话
session = client.create_session(username="eval_user")

# 发送消息
response = client.enqueue_message(
    session_id=session_id,
    username="eval_user",
    message="..."
)
```

主要方法：
- `retrieve_documents(persona_id, query, username, top_k)` → List[Document]
- `ingest_text(persona_id, username, text)` → Dict
- `create_session(username)` → Dict
- `enqueue_message(session_id, username, message)` → Dict
- `list_messages(session_id, username)` → List[Dict]

## 数据集格式

### product_qa.json (RAG 数据)

```json
[
  {
    "id": "qa_001",
    "question": "什么是机器学习?",
    "answer": "机器学习是...",
    "document": "完整文档内容"
  }
]
```

### conversations.json (对话数据)

```json
[
  [
    {"speaker": "user", "message": "大家好"},
    {"speaker": "persona1", "message": "你好，我是..."},
    {"speaker": "persona2", "message": "很高兴认识你"}
  ]
]
```

### comparison_qa.json (对比数据)

```json
[
  {
    "id": "cmp_001",
    "query": "问题",
    "relevant_docs": ["doc_id1", "doc_id2"],
    "irrelevant_docs": ["doc_id3"]
  }
]
```

## 运行脚本参数

所有脚本支持以下参数：

```bash
uv run exp1_rag_evaluation.py \
  --seed 42                    # 随机种子
  --persona-id 1               # Persona ID
  --username eval_user         # 用户名
  --config-dir ../config       # 配置文件目录
  --data-dir ../datasets       # 数据文件目录
  --output-dir ../results      # 结果输出目录
```

## 查看结果

实验完成后，查看结果：

```bash
# 查看 JSON 结果
cat results/exp1_results.json | python3 -m json.tool

# 查看所有结果摘要
cd scripts
uv run summarize_results.py
```

## 故障排除

### 后端连接失败

```bash
# 检查后端是否在运行
curl http://localhost:8000/api/personas

# 查看后端日志
tail -f logs/backend.log
```

### 数据初始化失败

```bash
# 确保后端正在运行
lsof -i :8000

# 重试初始化
python3 scripts/init_backend.py --backend-url http://localhost:8000
```

### 实验超时

增加脚本的超时时间或检查后端性能：

```bash
# 检查后端日志中的性能问题
tail -100 /path/to/Mul_in_ONE/logs/backend.log | grep -i error
```

## 环境变量

可通过环境变量自定义配置：

```bash
# 后端 URL
export BACKEND_URL=http://localhost:9000

# API 密钥
export SILICONFLOW_API_KEY=sk-xxx
export GOOGLE_EMBEDDING_API_KEY=AIza-xxx

# 运行实验
uv run exp1_rag_evaluation.py
```

## 相关文档

- [系统架构](../docs/architecture.md)
- [后端 API 文档](../docs/api.md)

## 许可

MIT License - 详见项目根目录
