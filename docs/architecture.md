# Mio 平台架构设计文档

## 1. 项目概述

Mio（Mul-in-One）是一个 Persona 驱动、RAG 增强、可观测编排的多智能体协作系统。基于 NVIDIA NeMo Agent Toolkit 构建,面向企业知识问答与复杂任务执行场景,实现从意图解析到跨智能体闭环协作的工程化落地。系统支持多租户 SaaS 架构,提供完整的数据库持久化、REST/WebSocket 实时通信及前端可视化交互能力。

## 2. 架构设计原则

### 2.1 核心设计理念

1. **模块化与可扩展性**

   - 清晰的分层架构,服务间低耦合高内聚
   - 插件化 Persona 与工具函数注册机制
   - 支持多 LLM 提供商动态切换
2. **多租户隔离与安全**

   - 数据库层面的租户分区(Tenant Isolation)
   - Milvus Collection 按 Persona 隔离存储
   - API 密钥加密存储,HTTPS/WSS 加密传输
3. **可观测性与可解释性**

   - 完整的链路追踪(请求→检索→生成→输出)
   - 指标驱动的策略优化(Recall@K, MRR, 时延)
   - 生成结果附带知识来源标注
4. **高性能与低时延**

   - 异步 I/O(FastAPI + SQLAlchemy Async)
   - Milvus HNSW 索引实现毫秒级检索
   - WebSocket 流式输出,降低首字时延

### 2.2 技术选型理由

| 技术栈               | 选型                      | 理由                                               |
| -------------------- | ------------------------- | -------------------------------------------------- |
| **后端框架**   | FastAPI                   | 原生异步支持,高性能,自动生成 OpenAPI 文档          |
| **数据库**     | PostgreSQL                | 成熟的关系型数据库,支持 JSONB 与复杂查询           |
| **ORM**        | SQLAlchemy 2.0            | 异步支持,类型安全,灵活的查询 DSL                   |
| **向量数据库** | Milvus                    | 开源高性能,支持 HNSW/IVF 多种索引,易于扩展         |
| **对话引擎**   | NVIDIA NeMo Agent Toolkit | 企业级多智能体框架,工具链成熟,社区活跃             |
| **RAG 集成**   | LangChain                 | 丰富的 Loader/Splitter 组件,Embedding 模型集成完善 |
| **前端框架**   | Vue 3 + Vite              | 组合式 API,响应式系统,开发体验优秀                 |
| **UI 组件库**  | Quasar                    | Material Design,跨平台,组件丰富                    |

## 3. 技术栈概览

### 3.1 后端技术栈

- **编程语言**: Python 3.11+
- **Web框架**: FastAPI
- **数据库**: PostgreSQL (主要), SQLite (测试)
- **ORM**: SQLAlchemy (异步)
- **数据库迁移**: Alembic
- **对话引擎**: NVIDIA NeMo Agent Toolkit（工具优先、函数调用）
- **RAG 集成**: LangChain, OpenAIEmbeddings, OpenAI
- **向量数据库**: Milvus
- **包管理**: uv

### 3.2 前端技术栈

- **框架**: Vue.js 3
- **构建工具**: Vite
- **UI组件库**: Quasar
- **状态管理**: Vue Composition API
- **包管理**: npm

### 3.3 开发环境

- **环境管理**: Nix
- **Python虚拟环境**: uv

## 4. 系统总体架构

```mermaid
graph TD
    A[用户] --> B[前端应用]
    B --> C[后端服务]
    C --> D[数据库]
    C --> E[NVIDIA NeMo Agent Toolkit]
    C --> M[Milvus 向量数据库]
    E --> F[LLM API]
  
    subgraph 前端
        B
    end
  
    subgraph 后端
        C
        E
    end
  
    subgraph 外部服务
        F
    end
  
    subgraph 数据存储
        D
        M
    end
```

## 后端组件依赖关系

### 核心模块

1. **主应用模块** ([src/mul_in_one_nemo/service/app.py](src/mul_in_one_nemo/service/app.py:10))

   - 创建 FastAPI 应用实例
   - 注册路由模块
2. **配置模块** ([src/mul_in_one_nemo/config.py](src/mul_in_one_nemo/config.py:26))

   - 管理应用配置
   - 从环境变量加载配置
   - 支持数据库URL、API密钥等配置项
3. **数据库模块** ([src/mul_in_one_nemo/db/](src/mul_in_one_nemo/db/__init__.py:15))

   - 数据库连接管理
   - 异步会话工厂
   - 会话上下文管理器
4. **模型模块** ([src/mul_in_one_nemo/db/models.py](src/mul_in_one_nemo/db/models.py:22))

   - 数据库表结构定义
   - SQLAlchemy 模型类
   - 包含 Tenant、User、APIProfile、Persona、Session、SessionMessage 等模型
5. **服务模块** ([src/mul_in_one_nemo/service/](src/mul_in_one_nemo/service/__init__.py:1))

   - 业务逻辑实现
   - API 路由处理
   - 会话管理服务
6. **路由模块** ([src/mul_in_one_nemo/service/routers/](src/mul_in_one_nemo/service/routers/__init__.py:1))

   - 会话相关路由 ([sessions.py](src/mul_in_one_nemo/service/routers/sessions.py:13))
   - Persona 和 API Profile 路由 ([personas.py](src/mul_in_one_nemo/service/routers/personas.py:14))
7. **仓库模块** ([src/mul_in_one_nemo/service/repositories.py](src/mul_in_one_nemo/service/repositories.py:22))

   - 数据访问层实现
   - SQLAlchemy 查询封装
   - 包含 SessionRepository、PersonaDataRepository 等
8. **依赖注入模块** ([src/mul_in_one_nemo/service/dependencies.py](src/mul_in_one_nemo/service/dependencies.py:24))

   - FastAPI 依赖注入配置
   - 单例模式实现
   - 服务实例管理
   9. **运行时模块** ([src/mul_in_one_nemo/runtime.py](src/mul_in_one_nemo/runtime.py:19))
   
   - 与 NVIDIA NeMo Agent Toolkit 集成
   - 多智能体运行时环境
   - 注册 Persona 函数与通用工具（WebSearch、RagQuery）
10. **调度器模块** ([src/mul_in_one_nemo/scheduler.py](src/mul_in_one_nemo/scheduler.py:19))

    - 多智能体对话调度
    - 主动性计算
    - 冷却机制管理
11. **内存管理模块** ([src/mul_in_one_nemo/memory.py](src/mul_in_one_nemo/memory.py:20))

    - 对话历史管理
    - 消息存储和检索
12. **Persona模块** ([src/mul_in_one_nemo/persona.py](src/mul_in_one_nemo/persona.py:10))

    - Persona 模型定义
    - YAML 配置文件加载
    - Persona 设置管理
13. **CLI模块** ([src/mul_in_one_nemo/cli.py](src/mul_in_one_nemo/cli.py:36))

    - 命令行接口实现
    - 交互式对话驱动
14. **RAG服务模块** ([src/mul_in_one_nemo/service/rag_service.py](src/mul_in_one_nemo/service/rag_service.py:1))

    - 知识库摄取（URL/文本）
    - Milvus 向量存储集成
    - 文档检索（供 RagQuery 工具调用）
15. **工具模块**（NAT 标准化实现）
    - **WebSearch 工具** ([src/mul_in_one_nemo/tools/web_search_tool.py](src/mul_in_one_nemo/tools/web_search_tool.py))
      - 自包含实现：内置 DuckDuckGo HTML 搜索和页面抓取
      - 输入：query, top_k, fetch_snippets
      - 输出：title, url, snippet（可选）
      - 无外部依赖服务，直接使用 httpx 和正则解析
    - **RagQuery 工具** ([src/mul_in_one_nemo/tools/rag_query_tool.py](src/mul_in_one_nemo/tools/rag_query_tool.py))
      - 封装 RAGService.retrieve_documents
      - 输入：query, persona_id, top_k
      - 输出：passages（text + source）
      - LLM 按需调用，无预注入行为

    - LangChain 集成（Embeddings, LLM）
    - 数据库配置动态解析
15. **RAG依赖模块** ([src/mul_in_one_nemo/service/rag_dependencies.py](src/mul_in_one_nemo/service/rag_dependencies.py:1))

    - 轻量级单例访问器
    - 避免循环依赖

### 后端数据流动逻辑

```mermaid
graph LR
    A[用户请求] --> B[FastAPI路由]
    B --> C[依赖注入]
    C --> D[服务层]
    D --> E[仓库层]
    E --> F[数据库]
    D --> G[运行时适配器]
    G --> H[NVIDIA NeMo Agent Toolkit]
    H --> I[LLM API]
    I --> H
    H --> G
    G --> D
    D --> J[WebSocket推送]
    J --> K[前端客户端]
```

1. **API请求处理流程**:

   - 用户发起 HTTP 请求到 FastAPI 路由
   - 通过依赖注入获取服务实例
   - 服务层调用仓库层进行数据操作
   - 数据库持久化存储
   - 返回响应给前端
2. **对话处理流程**:

   - 用户通过 WebSocket 发送消息
   - 后端接收消息并存储到数据库
   - SessionService 处理消息并调用 RuntimeAdapter
   - RuntimeAdapter 调用 NVIDIA NeMo Agent Toolkit
   - 多个 Agent 依次生成响应
   - 响应通过 WebSocket 实时推送给前端
3. **Persona管理流程**:

   - 通过 REST API 管理 Persona 配置
   - Persona 数据存储在数据库中
   - 运行时从数据库加载 Persona 配置
   - 与 NVIDIA NeMo Agent Toolkit 集成

## 前端组件依赖关系

### 核心模块

1. **主应用** ([src/mio_frontend/mio-frontend/src/App.vue](src/mio_frontend/mio-frontend/src/App.vue:1))

   - 应用根组件
   - 路由视图容器
2. **路由配置** ([src/mio_frontend/mio-frontend/src/router/index.ts](src/mio_frontend/mio-frontend/src/router/index.ts:10))

   - 页面路由定义
   - 路由守卫实现
   - 页面组件映射
3. **API通信模块** ([src/mio_frontend/mio-frontend/src/api.ts](src/mio_frontend/mio-frontend/src/api.ts:26))

   - REST API 调用封装
   - 请求拦截器配置
   - 认证状态管理
4. **WebSocket模块** ([src/mio_frontend/mio-frontend/src/websocket.ts](src/mio_frontend/mio-frontend/src/websocket.ts:23))

   - WebSocket 客户端实现
   - 自动重连机制
   - 消息处理封装
5. **聊天状态管理** ([src/mio_frontend/mio-frontend/src/composables/useChat.ts](src/mio_frontend/mio-frontend/src/composables/useChat.ts:4))

   - 聊天状态组合式函数
   - 消息流管理
   - WebSocket 连接管理
6. **UI组件**:

   - 登录页面 ([LoginPage.vue](src/mio_frontend/mio-frontend/src/pages/LoginPage.vue:1))
   - 会话列表页面 ([SessionsPage.vue](src/mio_frontend/mio-frontend/src/pages/SessionsPage.vue:1))
   - Persona管理页面 ([PersonasPage.vue](src/mio_frontend/mio-frontend/src/pages/PersonasPage.vue:1))
   - API Profile管理页面 ([ApiProfilesPage.vue](src/mio_frontend/mio-frontend/src/pages/ApiProfilesPage.vue:1))
   - 聊天对话页面 ([ChatConversationPage.vue](src/mio_frontend/mio-frontend/src/pages/ChatConversationPage.vue:1))

### 前端数据流动逻辑

```mermaid
graph LR
    A[用户交互] --> B[Vue组件]
    B --> C[API模块]
    C --> D[后端REST API]
    D --> C
    C --> B
    B --> E[状态更新]
    E --> F[UI渲染]
  
    G[后端WebSocket] --> H[WebSocket模块]
    H --> I[聊天状态]
    I --> F
```

1. **页面加载流程**:

   - 路由匹配加载对应页面组件
   - 组件挂载时调用 API 获取数据
   - 数据存储在组件状态中
   - 通过 Vue 响应式系统更新 UI
2. **聊天消息流程**:

   - 用户输入消息通过 WebSocket 发送到后端
   - 后端处理消息并生成 Agent 响应
   - Agent 响应通过 WebSocket 实时推送
   - 前端接收消息并更新聊天状态
   - Vue 响应式系统自动更新 UI
3. **数据管理流程**:

   - 通过 API 模块与后端 REST API 交互
   - 使用 Axios 进行 HTTP 请求
   - 请求拦截器自动添加认证信息
   - 响应数据存储在组件状态中

## 业务逻辑

### 核心业务实体

1. **Tenant (租户)**:

   - 多租户架构支持
   - 用户和资源隔离
2. **User (用户)**:

   - 用户身份管理
   - 与租户关联
3. **Persona (角色)**:

   - AI Agent 的人格定义
   - 包含名称、提示词、语调等属性
   - 可绑定不同的 LLM API 配置
   - 支持背景经历字段（自动摄取到 RAG 知识库，通过向量检索增强对话）
4. **API Profile (API配置)**:

   - LLM API 连接配置
   - 包含基础URL、模型名称、API密钥等
   - 运行时动态解析为 Persona 提供配置
5. **Session (会话)**:

   - 用户与 Agent 的对话会话
   - 包含会话历史和参与者信息
   - 支持无限历史窗口（memory_window = -1）
6. **SessionMessage (会话消息)**:

   - 会话中的具体消息
   - 包含发送者、内容等信息
7. **RAG 知识库**:

   - 按 Persona 分集存储在 Milvus 中
   - 支持 URL 抓取和直接文本摄取
   - 向量检索增强对话上下文

### 5.2 RAG 检索增强模块

#### 5.2.1 RAG 系统设计概述

Mio 的 RAG 系统是多智能体对话的核心支撑模块，通过向量化检索为每个 Persona 提供专属的知识库支持，显著提升生成内容的准确性与领域相关性。

#### 5.2.2 RAG 系统架构层次

```mermaid
graph TB
    subgraph 数据摄取层
        D1[URL 抓取] --> Parser[文档解析器]
        D2[文本上传] --> Parser
        D3[Persona 背景] --> Parser
        Parser --> Splitter[文本分块器<br/>RecursiveCharacterTextSplitter]
    end
  
    subgraph 向量化层
        Splitter --> Embed[Embedding API<br/>OpenAI/bge/e5]
        Embed --> VecStore[向量存储]
    end
  
    subgraph 存储层
        VecStore --> Milvus[(Milvus 向量数据库)]
        Milvus --> C1[persona_1_collection]
        Milvus --> C2[persona_2_collection]
        Milvus --> CN[persona_N_collection]
    end
  
    subgraph 检索层
        Query[用户查询] --> QEmbed[查询向量化]
        QEmbed --> Search[相似度检索<br/>HNSW/IVF索引]
        Search --> Milvus
        Milvus --> TopK[Top-K 文档片段]
    end
  
    subgraph 生成层
        TopK --> Context[上下文构建]
        SysPrompt[System Prompt] --> Context
        History[历史对话] --> Context
        Context --> LLM[LLM 生成]
        LLM --> Output[增强回复]
    end
```

#### 5.2.3 数据摄取与向量化流程

**1. 文档摄取（Ingestion）**

Mio 支持多种数据源的知识库构建：

- **URL 抓取**: 通过 `WebBaseLoader` 自动抓取网页内容，提取正文并清洗格式
- **文本上传**: 直接接收用户提交的文本内容（如产品说明、技术文档、FAQ）
- **Persona 背景**: 自动将 Persona 的 `background` 字段摄取到其专属知识库

**2. 文本分块（Chunking）**

采用 `RecursiveCharacterTextSplitter` 进行智能分块：

- **块大小（chunk_size）**: 默认 1000 字符，保证语义完整性
- **重叠（overlap）**: 200 字符重叠，避免上下文截断
- **分隔符优先级**: 按段落 → 句子 → 单词层级递归切分

**3. 向量化（Embedding）**

- **模型选择**: 支持 OpenAI Embeddings、bge-large-zh、e5-large-v2 等主流嵌入模型
- **维度**: 根据模型选择（如 OpenAI text-embedding-3-small: 1536 维）
- **归一化**: 自动进行 L2 归一化，提升相似度计算精度
- **批量处理**: 批量调用 Embedding API，提升摄取效率

```mermaid
sequenceDiagram
    participant User as 用户/管理员
    participant API as 后端 API
    participant RAG as RAGService
    participant Loader as 文档加载器
    participant Splitter as 文本分块器
    participant Embed as Embedding API
    participant Milvus as Milvus 数据库
  
    User->>API: POST /personas/{id}/ingest<br/>{url/text}
    API->>RAG: ingest_url(url, persona_id)
    RAG->>Loader: 加载文档内容
    Loader-->>RAG: 返回原始文本
  
    RAG->>Splitter: 文本分块<br/>chunk_size=1000, overlap=200
    Splitter-->>RAG: 返回文本块列表
  
    loop 批量向量化
        RAG->>Embed: 调用 Embeddings API
        Embed-->>RAG: 返回向量 (1536维)
    end
  
    RAG->>Milvus: 插入向量到<br/>persona_{id}_collection
    Milvus-->>RAG: 确认存储成功
    RAG-->>API: 返回摄取结果<br/>{文档数, 向量数}
    API-->>User: 显示摄取成功
```

#### 5.2.4 向量检索与相似度计算

**1. 索引结构**

Milvus 采用 **HNSW（Hierarchical Navigable Small World）** 索引：

- **搜索复杂度**: O(log N)，支持百万级向量毫秒级检索
- **参数配置**:
  - `M`: 每层最大连接数（默认 16）
  - `efConstruction`: 构建时搜索深度（默认 200）
  - `ef`: 查询时搜索深度（默认 64）

**2. 相似度度量**

- **度量方式**: 余弦相似度（Cosine Similarity）或内积（Inner Product）
- **归一化**: 向量存储前自动归一化为单位向量
- **Top-K 检索**: 默认返回相似度最高的 3-5 个文档片段

**3. 混合检索（Hybrid Search）**

支持向量检索 + 标量过滤：

- **租户隔离**: 按 `persona_id` 分集存储，保证多租户数据隔离
- **元数据过滤**: 可按 `source`（来源URL）、`timestamp`（摄取时间）等字段过滤
- **重排序**: 检索后可按业务规则（如时效性、权威性）二次排序

```mermaid
flowchart LR
    Query[用户查询<br/>我想了解产品A的特性] --> Embed[向量化查询]
    Embed --> Vec[查询向量<br/>1536维]
  
    Vec --> Milvus[(Milvus)]
    Milvus --> Filter{按 persona_id 分区}
    Filter --> Search[HNSW 索引检索<br/>Top-K=5]
  
    Search --> Results[检索结果]
    Results --> R1["文档1: 产品A采用...<br/>相似度: 0.92"]
    Results --> R2["文档2: 产品A的核心特性...<br/>相似度: 0.89"]
    Results --> R3["文档3: 用户反馈显示...<br/>相似度: 0.85"]
  
    R1 --> Context[构建增强上下文]
    R2 --> Context
    R3 --> Context
  
    Context --> Prompt[融合到 System Prompt]
    Prompt --> LLM[LLM 生成]
```

#### 5.2.5 上下文注入与生成增强

**1. 上下文构建策略**

检索到的 Top-K 文档片段按以下结构注入到 Prompt：

```
[System Prompt]
{Persona 设定与能力描述}

[Knowledge Base Context]
根据你的知识库，以下是相关参考信息：
1. [来源: URL/文档A] {文档片段1}
2. [来源: 文档B] {文档片段2}
3. [来源: 文档C] {文档片段3}

[Conversation History]
{最近N轮对话历史}

[Current Query]
用户: {当前问题}
```

**2. 动态上下文窗口管理**

- **Token 预算**: 根据模型上下文限制（如 GPT-4: 8K/32K tokens）动态调整检索数量
- **优先级策略**:
  1. System Prompt（必需）
  2. Top-K 检索结果（核心知识）
  3. 最近 N 轮历史（上下文连贯性）
  4. 早期历史（按需裁剪）

**3. 生成质量保障**

- **来源标注**: 生成回复时自动附带知识来源（如"根据产品文档A..."）
- **置信度评估**: 根据检索相似度判断回复可信度
- **幻觉检测**: 低相似度时触发"我不确定"机制，避免编造事实

```mermaid
sequenceDiagram
    participant User as 用户
    participant Agent as Agent Runtime
    participant RAG as RAGService
    participant Milvus as Milvus
    participant LLM as LLM API
  
    User->>Agent: 查询: 产品A的保修政策是什么?
    Agent->>RAG: retrieve_documents(query, persona_id)
    RAG->>RAG: 向量化查询
    RAG->>Milvus: 相似度检索 Top-5
    Milvus-->>RAG: 返回文档片段 + 相似度分数
  
    RAG->>RAG: 过滤低相似度文档 (< 0.7)
    RAG->>RAG: 构建增强上下文
    RAG-->>Agent: 返回格式化上下文
  
    Agent->>Agent: 融合 System Prompt + 上下文 + 历史
    Agent->>LLM: 调用生成 API
    LLM-->>Agent: 流式返回生成内容
  
    Agent->>Agent: 附加来源标注<br/>[来源: 产品文档 v2.1]
    Agent-->>User: 产品A提供2年保修...<br/>(来源已标注)
```

#### 5.2.6 知识库管理与优化

**1. 数据更新与版本控制**

- **增量更新**: 支持追加新文档而不重建整个索引
- **文档去重**: 基于内容哈希避免重复摄取
- **版本标记**: 每个文档片段记录 `ingestion_timestamp` 与 `version`

**2. 索引优化**

- **定期重建**: 在知识库规模变化 >20% 时触发索引重建，优化检索性能
- **分区策略**: 按 Persona 分集，避免跨租户检索干扰
- **TTL 清理**: 可配置文档过期时间，自动清理过时知识

**3. 质量监控**

- **检索质量指标**:
  - Recall@K: 前K个结果的召回率
  - MRR (Mean Reciprocal Rank): 首个相关文档的平均倒数排名
  - nDCG: 归一化折损累计增益
- **A/B 测试**: 支持不同 Embedding 模型、分块策略的效果对比
- **用户反馈**: 收集"答案是否有帮助"反馈，持续优化检索策略

## 6. 业务流程与数据流

### 6.1 核心业务流转机制

本节分三个业务流转核心：最短链路—租户选中一个Persona—生成反馈"你"闭环（打通Persona的闭环流程）

##### 6.1.1 业务流程序列图

```mermaid
sequenceDiagram
    participant User as 租户
    participant Service as 服务层
    participant Persona as Persona管理
    participant RAG as RAG服务
    participant Agent as Agent Runtime
  
    %% 1. 建表建立与租户注册
    Note over User,Persona: 1. 建表建立与租户注册
    User->>Service: 创建租户请求
    Service->>Persona: 初始化 tenant_id 与 persona_id
    Persona-->>Service: 返回租户与角色配置，从数据库验证通过后<br/>系统根据动态API配置，启动对应的 Agent Runtime
  
    %% 2. 消息接收与意图分发
    Note over User,Agent: 2. 消息接收与意图分发
    User->>Service: 提交用户输入
    Service->>Persona: 获取 Persona 配置，被选人化与数数据库
    Service->>Agent: 计算解析有意图 Agent 的构建概念，确定下一轮攻的发言角色
  
    %% 3. 检索增强与上下文链 (RAG Process)
    Note over Agent,RAG: 3. 检索增强与上下文链 (RAG Process)
    Agent->>RAG: 请求语义检索
    RAG-->>Agent: 返回 Top-K 相关文档片段，外部无源雷达合作 System Message<br/>构建最终 Prompt，构建用户历史追踪状态信息
  
    %% 4. 推理生成与流式返回
    Note over Agent,User: 4. 推理生成与流式返回
    Agent->>Agent: 通过 LLM API 进行推理，生成的 Token 流经由前端服务进行协议<br/>通过 WebSocket 或流式时返到前端，前端循环 SSE 协议<br/>向前端做反馈，实时写流的逐字显示
    Agent-->>User: 流式返回生成内容
```

##### 6.1.2 关键步骤说明

**1. 建表建立与租户注册**

- 用户注册并获得 `tenant_id`
- 系统初始化 Persona 配置（从 `persona.yaml` 与 `api_configuration.yaml` 解析）
- 动态绑定 API 配置，准备 Agent Runtime 所需资源
- 在 Milvus 与数据库中建立租户分区

**2. 消息接收与意图分发**

- 前端提交用户输入与选定的 `persona_id`
- 服务层解析意图，判定所需工具与 RAG 策略
- 加载历史会话记忆与 System Message，构建完整上下文
- 启动对应 Persona 的 Agent Runtime

**3. 检索增强与调用外链 (RAG Process)**

- Agent 向 RAG 服务请求，RAG 服务查询 Milvus 获取 Top-K 相似文档片段
- 外部工具（如无源雷达专家系统、企业知识库）并行检索，合并结果
- 对检索结果进行去重、排序与标签过滤（Hybrid Search）
- 将增强上下文融合到 Prompt，形成最终输入

**4. 反馈与记忆更新**

- Agent 生成回复后，将本轮对话、工具调用记录与状态持久化到会话记忆
- 返回生成结果与元数据（如来源文档、置信度、执行链路）
- 前端展示结果并提供可解释性信息（如"答案来源：文档A第3段"）

**5. 可观测与闭环优化**

- 记录关键指标：检索时延、命中率（Recall@K）、工具调用成功率、生成质量评分
- 定期评估策略效果，触发 Persona 配置或 RAG 参数调整
- 形成"计划—执行—评估—优化"的闭环

##### 6.1.3 技术亮点

- **人设持久化**：Persona 配置驱动能力边界与工具权限，保障上下文一致性
- **动态 RAG**：支持在线数据注入与索引重建，混合检索提升召回质量
- **可观测编排**：链路追踪、指标驱动、策略迭代，形成闭环优化
- **多租户隔离**：租户级数据分区与配额管理，保障 SaaS 交付稳定性

### 6.2 多智能体对话流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant N as NeMo Toolkit
    participant L as LLM API
  
    U->>F: 发送消息
    F->>B: WebSocket消息
    B->>B: 存储消息到数据库
    B->>N: 调用运行时适配器
    loop 每个Agent
        N->>L: 调用LLM API
        L->>N: 返回响应
        N->>B: 流式返回响应
        B->>F: WebSocket推送
        F->>U: 实时显示
    end
```

1. 用户在前端界面输入消息
2. 前端通过 WebSocket 将消息发送到后端
3. 后端接收消息并存储到数据库
4. SessionService 调用 RuntimeAdapter 处理消息
5. RuntimeAdapter 调用 NVIDIA NeMo Agent Toolkit
6. 多个 Agent 依次调用 LLM API 生成响应
7. Agent 响应通过 WebSocket 实时推送给前端
8. 前端实时显示 Agent 响应

### 6.3 Persona管理流程

1. 用户通过前端界面创建/编辑 Persona
2. 前端调用 REST API 将 Persona 数据发送到后端
3. 后端验证数据并存储到数据库
4. 运行时从数据库加载最新的 Persona 配置
5. 新的对话会话使用更新后的 Persona 配置

### 6.4 API Profile管理流程

1. 用户通过前端界面创建/编辑 API Profile
2. 前端调用 REST API 将 API Profile 数据发送到后端
3. 后端验证数据并加密存储 API 密钥到数据库
4. Persona 可以绑定到特定的 API Profile
5. 运行时根据绑定关系使用相应的 API 配置

#### 4. RAG 知识库管理流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant R as RAGService
    participant M as Milvus
    participant L as LLM
  
    U->>F: 提交知识内容（URL/文本）
    F->>B: POST /personas/{id}/ingest
    B->>R: 调用 ingest_url/ingest_text
    R->>R: 抓取/解析文本
    R->>R: 文本切片 (RecursiveCharacterTextSplitter)
    R->>L: 调用 Embeddings API 生成向量
    L->>R: 返回向量
    R->>M: 存储到 persona_{id}_collection
    M->>R: 确认存储成功
    R->>B: 返回摄取结果
    B->>F: 返回状态与文档数
    F->>U: 显示摄取成功
```

**知识检索与工具化调用流程**:

```mermaid
sequenceDiagram
    participant U as 用户
    participant B as 后端
    participant P as PersonaFunction
    participant T as NAT Tools
    participant R as RAGService
    participant M as Milvus
    participant L as LLM
  
    U->>B: 发送对话消息
    B->>P: 调用 _build_prompts (async)
    Note over P: 工具优先：无预注入，LLM 按需调用工具
    P->>L: 发送 System Prompt + 工具定义 + 历史 + 用户消息
    L->>L: 决策：是否调用工具？
    alt LLM 决定调用 RagQuery
        L->>T: 调用 RagQuery(query, persona_id)
        T->>R: retrieve_documents
        R->>M: 向量相似度检索
        M->>R: 返回 Top-K 文档
        R->>T: 格式化文档
        T->>L: 返回工具结果（passages）
        L->>L: 融合工具结果到回答
    end
    L->>P: 流式返回响应
    P->>B: 返回生成结果
    B->>U: WebSocket 推送
```

## 5. 核心模块设计

### 5.1 多智能体协同模块

#### 5.1.1 多智能体协作模型

Mio 采用"异构体协作"系统。用户提问后，系统自动挑选"合适"的多智能体来交互式协作，本节结合 NVIDIA 的 Agent Runtime（"nemo_agentity"套接字/客户端（"Cooldown"机制），概括了基本人类群组交流的语境和生成过程。

##### 5.1.1.1 智能体协作框架（Agent Runtime Model）

Mio 系统在运行时采用 NVIDIA NeMo Agent Runtime 作为多智能体协作的核心框架，每个智能体包含三个核心层面：

- **状态层（State）**: 维护 Agent 自身状态（如冷却计数器、历史发言次数等）
- **策略层（Policy）**: 根据系统提示词（System Prompt）、动态配置及业务需求动态调整发言策略
- **交互层（Interaction）**: 通过工具函数（如 RAG 检索、外部 API 调用）与其他组件或 Agent 协作

```mermaid
graph TB
    subgraph Agent Runtime
        A1[Agent 1<br/>System Prompt + Policy]
        A2[Agent 2<br/>System Prompt + Policy]
        A3[Agent N<br/>System Prompt + Policy]
    end
  
    S[Scheduler<br/>调度器] --> A1
    S --> A2
    S --> A3
  
    A1 --> T[Thinking 思考评分]
    A2 --> SP[Speaking 发言锁定]
    A3 --> CD[Cooldown 冷却期]
  
    T --> Score[动态打分算法]
    SP --> LLM[LLM 生成]
    CD --> Wait[等待唤醒]
  
    Score --> S
    LLM --> Output[流式输出]
    Wait --> S
```

##### 5.1.1.2 基于状态机的动态调度策略

Mio 采用动态调度器（Scheduler）在多个 Agent 之间进行任务分发和协同，系统统一管理多智能体的发言次序和任务编排。调度器采用一个基于动态打分的算法来决定下一轮发言者：

**调度算法核心公式**：

$$
Score(a_i) = \alpha \cdot P_{\text{act}}(a_i) + \beta \cdot Rel(C_{\text{hist}}, a_i) - \gamma \cdot I_{\text{cool}}(a_i) + \delta \cdot M_{\text{mention}}(a_i)
$$

其中：

- $P_{\text{act}}(a_i)$: 智能体的固有主动性概率
- $Rel(C_{\text{hist}}, a_i)$: 历史上下文相关性（通过计算当前对话历史与 Agent System Prompt 的语义相关性）
- $I_{\text{cool}}(a_i)$: 冷却惩罚因子，若处于冷却期则为大于 0，否则为 0
- $M_{\text{mention}}(a_i)$: @提及奖励，若被用户 @ 提及则给高权重加成
- $\alpha, \beta, \gamma, \delta$: 各维度的超参数权重

系统根据 $Score(a_i)$ 降序排列并选出当前得分最高的 Agent 进行下一轮发言。

```mermaid
flowchart TD
    Start[用户消息到达] --> LoadAgents[加载会话所有 Agents]
    LoadAgents --> CalcScores[计算各 Agent Score]
  
    CalcScores --> CompThinking{是否处于 Thinking 阶段?}
    CompThinking -->|是| EvalContext[评估上下文相关性]
    CompThinking -->|否| CheckSpeaking{是否有 Agent 正在 Speaking?}
  
    EvalContext --> ScoreFormula["应用打分公式 Score = α·P + β·Rel - γ·Cool + δ·Mention"]
    ScoreFormula --> RankAgents[按得分降序排列]
  
    CheckSpeaking -->|是| WaitComplete[等待当前 Agent 完成]
    CheckSpeaking -->|否| RankAgents
  
    RankAgents --> SelectTop[选择得分最高 Agent]
    SelectTop --> LockAgent[锁定该 Agent 进入 Speaking]
    LockAgent --> CallLLM[调用 LLM 生成回复]
    CallLLM --> StreamOutput[流式输出到前端]
    StreamOutput --> UpdateCooldown[更新该 Agent 冷却状态]
    UpdateCooldown --> CheckMore{是否需要继续多轮?}
  
    CheckMore -->|是| CalcScores
    CheckMore -->|否| End[对话暂停/等待用户]
    WaitComplete --> CalcScores
```

##### 5.1.1.3 Agent 状态转换（Thinking → Speaking → Cooldown）

Mio 中每个 Agent 在一次对话周期内经历三种状态：

1. **Thinking（思考）**: Agent 根据当前上下文计算自身的发言意愿分数，此时尚未锁定 LLM 调用
2. **Speaking（发言）**: 获得锁定（Lock）的 Agent 调用 LLM 生成回复，并进入流式输出阶段
3. **Cooldown（冷却）**: 发言结束后，Agent 强制进入冷却期，避免连续垄断对话

**状态转换图**：

```mermaid
stateDiagram-v2
    [*] --> Idle: 初始化
    Idle --> Thinking: 新消息到达
    Thinking --> Speaking: 得分最高且未冷却
    Thinking --> Thinking: 得分不足/被其他Agent抢占
    Speaking --> Cooldown: 回复生成完成
    Cooldown --> Idle: 冷却期结束
    Idle --> Thinking: 下一轮消息
```

##### 5.1.1.4 冷却机制（Cooldown）详解

为避免单一 Agent 连续发言导致对话单调，Mio 引入**发言后冷却（Post-speaking Cooldown）**机制：

- **冷却计数器**: 每次 Agent 发言后，其冷却计数器设为预设值（如 2-3 轮）
- **惩罚项**: 在冷却期内，该 Agent 的 $I_{\text{cool}}(a_i)$ 项显著增大，导致 Score 降低
- **唤醒条件**:
  - 用户明确 @ 提及该 Agent（$M_{\text{mention}}$ 大幅提升可覆盖冷却惩罚）
  - 冷却计数器递减至 0
  - 系统检测到"冷场"（所有 Agent 得分均低于阈值），此时降低冷却惩罚以激活更多 Agent

**冷却与唤醒流程**：

```mermaid
sequenceDiagram
    participant User as 用户
    participant Scheduler as 调度器
    participant A1 as Agent 1 (刚发言)
    participant A2 as Agent 2
    participant A3 as Agent 3
  
    User->>Scheduler: 新消息
    Scheduler->>A1: 检查状态
    A1-->>Scheduler: Cooldown=2（惩罚-5分）
    Scheduler->>A2: 检查状态
    A2-->>Scheduler: Idle（正常计分）
    Scheduler->>A3: 检查状态
    A3-->>Scheduler: Idle（正常计分）
  
    Scheduler->>Scheduler: 计算 Score(A1)=-2, Score(A2)=7, Score(A3)=6
    Scheduler->>A2: 选中 Agent 2 发言
    A2->>User: 生成回复
    Scheduler->>A2: 设置 Cooldown=2
    Scheduler->>A1: Cooldown 递减至 1
  
    Note over User,A3: 下一轮消息
    User->>Scheduler: 新消息（@ Agent 1）
    Scheduler->>A1: 检查 @Mention 奖励
    A1-->>Scheduler: Mention Bonus=+10
    Scheduler->>Scheduler: Score(A1)=8（覆盖冷却惩罚）
    Scheduler->>A1: 强制唤醒并发言
```

### 6.5 调度机制

1. **主动性计算**:

   - 每个 Persona 有主动性属性 (0.0-1.0)
   - 根据上下文和历史对话计算发言概率
2. **冷却机制**:

   - 刚发过言的 Agent 进入冷却期
   - 避免单个 Agent 连续发言
3. **@提及机制**:

   - 用户可以 @ 特定的 Agent
   - 被提及的 Agent 必须回复
4. **冷场检测**:

   - 检测对话是否冷场
   - 降低发言阈值以激活更多 Agent

## 7. 部署架构

### 7.1 开发环境

1. **Nix环境管理** ([flake.nix](flake.nix:1))

   - 统一开发环境配置
   - 自动安装依赖项
2. **数据库管理**:

   - 本地 PostgreSQL 实例
   - 数据库迁移脚本 ([alembic/](alembic/env.py:1))

### 7.2 生产环境

1. **后端服务**:

   - FastAPI 应用
   - ASGI 服务器 (如 uvicorn)
   - 数据库连接池
2. **前端应用**:

   - 构建后的静态文件
   - Web 服务器 (如 nginx)
3. **数据库**:

   - PostgreSQL 数据库
   - 定期备份策略
4. **向量数据库**:

   - Milvus 实例（推荐 Docker 部署）
   - 持久化存储配置
   - 集合备份与恢复策略

## 8. 安全考虑

1. **API密钥加密**:

   - API 密钥在数据库中加密存储
   - 使用加密密钥进行加解密
2. **认证授权**:

   - 基于租户的资源隔离
   - 用户角色权限控制
3. **数据传输安全**:

   - HTTPS 加密传输
   - WebSocket 安全连接 (wss)

## 9. 扩展性设计

1. **插件化架构**:

   - 支持不同的 LLM 提供商
   - 可扩展的 Persona 功能
2. **多租户支持**:

   - 数据库层面的租户隔离
   - 可配置的资源限制
3. **微服务潜力**:

   - 模块化设计便于拆分
   - API 优先的设计理念

## 10. 总结

Mul-in-One 项目通过结合 FastAPI 的高性能后端和 Vue.js 的现代化前端，构建了一个功能完整的多智能体对话系统。系统充分利用了 NVIDIA NeMo Agent Toolkit 的强大能力，实现了自然流畅的多 Agent 对话体验。

**核心成就**:

- ✅ **完整的 RAG 集成**: 通过 Milvus 向量数据库和 LangChain，实现了知识库摄取、检索和生成全链路
- ✅ **数据库驱动配置**: 运行时动态解析 Persona 的 API 配置，支持多租户 SaaS 架构
- ✅ **灵活的会话语义**: 支持无限历史窗口和回合限制，适应不同对话场景
- ✅ **模块化架构**: 清晰的分层设计便于维护和扩展

通过清晰的架构设计和模块化实现，系统具有良好的可维护性和扩展性，为后续的检索质量优化、多模态支持和企业级功能提供了坚实基础。
