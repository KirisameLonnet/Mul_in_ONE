# Mul-in-One (MIO) - 多智能体对话系统

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11-3.13](https://img.shields.io/badge/python-3.11--3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)](https://vuejs.org/)

**一个功能完整的多智能体对话系统,支持动态 Persona 管理、RAG 知识增强、实时流式对话和 Web 可视化界面。**


demo已上线，欢迎前来帮我免费测试（
 > mio.lonnet.uk[https://mio.lonnet.uk]

本项目基于 NVIDIA NeMo Agent Toolkit 构建,提供了从命令行工具到 Web 应用的完整解决方案,让多个 AI Agent 能够像真人群聊一样进行自然、流畅的对话互动。系统采用“工具优先（NAT 函数调用）”设计,由 LLM 按需主动调用工具（如 WebSearch、RagQuery）,不再使用内联触发器或每轮预注入背景。

## ✨ 核心特性

### 🎭 智能 Persona 系统
- **动态配置管理**: 通过 Web 界面实时创建、编辑和删除 AI 人格
- **多维度人格设置**: 支持名称、handle、语气、主动性、记忆窗口等细粒度配置
- **背景知识库**: 为每个 Persona 配置背景传记,通过 RAG 自动转换为向量知识库
- **灵活 API 绑定**: 每个 Persona 可绑定不同的 LLM API 配置(模型、温度参数等)

### 🧠 RAG 知识增强系统
- **全局 Embedding 配置**: 租户级别的统一 embedding 模型配置
- **自动向量化**: 创建或更新 Persona 背景时自动分块、向量化并存储到 Milvus
 - **工具化按需检索**: 由 LLM 通过 `RagQuery` 工具按需检索相关背景,提升回复质量与可解释性（不再每轮预注入）
- **手动刷新控制**: 支持主动触发背景知识的重新摄取和索引

### 💬 高级对话功能
- **动态调度算法**: 基于主动性、上下文和话题相关性智能选择发言者
- **精准 Target 控制**: 用户可明确指定参与对话的 Agent,避免无关干扰
- **多轮自然对话**: 支持 Agent 之间的连续互动和话题延续
- **@提及机制**: 支持在消息中 @ 特定 Agent 强制其参与回复
- **用户 Persona**: 支持为用户设置角色扮演人格,影响 Agent 回复风格

### 🏗️ 完整的 Web 应用
- **现代化 UI**: 基于 Quasar 框架的响应式界面
- **会话管理**: 创建、列表、详情查看和删除对话会话
- **Persona 管理**: 可视化的 AI 人格 CRUD 操作界面
- **API Profile 管理**: 统一管理各种 LLM API 配置(OpenAI、SiliconFlow、自定义等)
- **Embedding 配置**: 独立的全局 embedding 模型配置面板
- **实时 DEBUG 日志**: 查看后端日志,监控 Milvus 和数据库操作
- **账户设置页面**: 查看账号属性、邮箱验证状态，并可执行危险操作（删除账号）

### 🔐 用户认证与安全
- **FastAPI-Users + JWT**: 提供登录、注册、邮箱验证、密码重置等完整认证流程
- **邮箱验证**: 可选配置 SMTP 服务器，自动发送注册验证/忘记密码邮件
- **Cloudflare Turnstile**: 可选启用人机验证，注册需携带 captcha token 才可通过
- **账户自助注销**: 新的 Account Settings 页面和 `DELETE /api/auth/account` 端点支持用户删除全部数据

### 🔧 开发者友好
- **RESTful API**: 完整的 FastAPI 后端,支持 Swagger 文档
- **数据库持久化**: PostgreSQL + Alembic 版本控制
- **向量数据库**: Milvus 高性能向量检索
- **热重载开发**: 前后端均支持代码修改后自动重载
- **NAT 工具优先**: 通过 NeMo Agent Toolkit 注册与发现工具,标准化 Web/RAG 能力,支持自定义工具扩展

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (异步 Web 框架)
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: PostgreSQL
- **向量数据库**: Milvus
 - **对话引擎**: NVIDIA NeMo Agent Toolkit（函数调用 / 工具优先）
- **LLM 集成**: LangChain, OpenAI SDK
- **包管理**: uv

### 前端
- **框架**: Vue 3 (Composition API)
- **UI 库**: Quasar Framework
- **HTTP 客户端**: Axios
- **WebSocket**: 原生 WebSocket API
- **构建工具**: Vite
- **包管理**: npm

## 🏗️ 项目结构

```
Mul_in_ONE/
├── alembic/                      # 数据库迁移脚本
│   ├── versions/                 # 迁移版本文件
│   └── env.py                    # Alembic 配置
├── docs/                         # 项目文档
│   ├── architecture.md           # 系统架构设计
│   ├── backend_service_design.md # 后端服务详细设计
│   └── roadmap.md                # 功能路线图
├── external/                     # 外部依赖
│   └── NeMo-Agent-Toolkit/       # NVIDIA NeMo Toolkit (子模块)
├── personas/                     # Persona 配置模板
│   ├── persona.yaml.example      # Persona 配置示例
│   └── api_configuration.yaml.example  # API 配置示例
├── scripts/                      # 辅助脚本
│   ├── bootstrap_toolkit.sh      # 初始化脚本
│   ├── db_control.sh             # 数据库控制脚本
│   └── milvus_control.sh         # Milvus 控制脚本
├── src/
│   ├── mio_frontend/             # 前端项目
│   │   └── mio-frontend/
│   │       ├── src/
│   │       │   ├── pages/        # 页面组件
│   │       │   │   ├── SessionsPage.vue       # 会话列表
│   │       │   │   ├── ChatConversationPage.vue  # 对话界面
│   │       │   │   ├── PersonasPage.vue       # Persona 管理
│   │       │   │   ├── APIProfilesPage.vue    # API 配置管理
│   │       │   │   └── DebugPage.vue          # DEBUG 日志
│   │       │   ├── layouts/      # 布局组件
│   │       │   ├── router/       # 路由配置
│   │       │   └── api.ts        # API 客户端
│   │       └── package.json
│   └── mul_in_one_nemo/          # 后端项目
│       ├── db/                   # 数据库层
│       │   └── models.py         # SQLAlchemy 模型
│       ├── service/              # 服务层
│       │   ├── app.py            # FastAPI 应用入口
│       │   ├── dependencies.py   # 依赖注入
│       │   ├── repositories.py   # 数据访问层
│       │   ├── session_service.py  # 会话服务
│       │   ├── rag_service.py    # RAG 服务
│       │   └── routers/          # API 路由
│       │       ├── sessions.py   # 会话 API
│       │       └── personas.py   # Persona API
│       ├── runtime.py            # NeMo 运行时封装
│       ├── tools/                # NAT 工具模块
│       │   ├── web_search_tool.py# WebSearch 工具 (公开信息检索, 自包含实现)
│       │   └── rag_query_tool.py # RagQuery 工具 (Persona 背景检索)
│       ├── scheduler.py          # 对话调度器
│       ├── memory.py             # 对话记忆管理
│       └── cli.py                # 命令行工具
├── tests/                        # 测试文件
├── pyproject.toml                # Python 项目配置
├── alembic.ini                   # Alembic 配置
└── README.md                     # 本文件
```

## 📚 详细文档

- [📐 系统架构设计](docs/architecture.md) - 整体架构、模块职责和数据流
- [⚙️ 后端服务设计](docs/backend_service_design.md) - API 接口、数据模型和实现细节
- [🗺️ 功能路线图](docs/roadmap.md) - 已完成功能和未来规划

## 🚀 快速开始

### 前置要求

- **Python 3.11-3.13（推荐 3.12）**
- **[uv](https://github.com/astral-sh/uv)** - 推荐的 Python 包管理器
- **Node.js 18+** 和 npm
- **PostgreSQL 14+**
- **Milvus** - 向量数据库 (推荐使用 Docker)
- **Docker** (可选,用于运行 Milvus)

> ℹ️ 目前 NVIDIA NeMo Agent Toolkit 在 Python 3.14 上存在 `TypeError: 'coroutine' object is not an async iterator` 的已知问题。请固定使用 3.11-3.13（推荐 3.12）。详见 `NAT_ISSUE_PYTHON314_COMPATIBILITY.md`。

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/KirisameLonnet/Mul_in_ONE.git
cd Mul_in_ONE
```

#### 2. 初始化后端

```bash
# 创建并激活 Python 虚拟环境
# NAT 在 Python 3.14 上存在已知问题，请固定到 3.12
uv python install 3.12
uv venv --python 3.12 .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 运行引导脚本 (自动克隆 NeMo Toolkit 并安装所有依赖)
./scripts/bootstrap_toolkit.sh
```

#### 3. 配置环境变量 ⚠️ **必须**

复制环境变量模板并配置：

```bash
cp .envrc.example .envrc
```

编辑 `.envrc` 文件，**必须配置**以下项：

```bash
# 数据库连接
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/mul_in_one"

# JWT 认证密钥（生产环境必须修改！使用下面的命令生成随机密钥）
export JWT_SECRET="your-secret-key-change-in-production"

# 生成安全的随机密钥（推荐）
# export JWT_SECRET="$(openssl rand -hex 32)"

# Docker 和 Milvus 配置（Milvus 启动必需）
export DOCKER_VOLUME_DIRECTORY="$(pwd)/external/NeMo-Agent-Toolkit/examples/deploy"
export MILVUS_CONFIG_DIR="$(pwd)/configs"
export MILVUS_MEM_LIMIT="6g"

# OAuth 配置（可选，如需第三方登录则取消注释）
# export GITEE_CLIENT_ID="your-gitee-client-id"
# export GITEE_CLIENT_SECRET="your-gitee-client-secret"
# export GITHUB_CLIENT_ID="your-github-client-id"
# export GITHUB_CLIENT_SECRET="your-github-client-secret"

# 其他配置见 .envrc.example 中的详细注释
```

加载环境变量：

```bash
direnv allow  # 如果使用 direnv（推荐）
# 或者手动加载
source .envrc
```

> 💡 **重要**: `DOCKER_VOLUME_DIRECTORY` 变量用于 Milvus Docker Compose 配置，指向 NeMo Toolkit 的 vendor volumes 根目录。如果不设置，Docker 会将路径解释为命名卷而非绑定挂载，导致 Milvus 无法正确读取配置文件。

> ⚠️ **重要安全提示**: 
> - `.envrc` 包含敏感信息（API密钥、数据库密码、JWT密钥等）
> - 该文件已自动加入 `.gitignore`，**请勿提交到版本控制系统**
> - 生产环境务必使用强随机密钥，不要使用示例中的默认值
>
> #### 🛡️ 隐私与本地文件隔离
> - 实际使用的 `.envrc` 已从 Git 追踪中移除并被忽略，继续使用 `.envrc.example` 作为模板，`cp .envrc.example .envrc` 后仅在本机保存真实凭据。
> - 本地运行生成的 `logs/`、`.postgresql/`、`.milvus/`、`*.db` 等目录/文件均在 `.gitignore` 中，避免误提交个人数据。
> - 如果之前已将真实密钥提交过仓库，请立即更换相关密钥/密码并在仓库中清理历史记录（如需要）。

> 📚 **认证系统文档**: 查看 [docs/authentication.md](docs/authentication.md) 了解完整的用户认证和 OAuth 配置指南

> 💡 **可选增强**: 若需开启邮箱验证或 Cloudflare Turnstile，请在 `.envrc` 中配置对应的 SMTP 与 `TURNSTILE_SECRET_KEY`，具体字段与示例可参考 `.envrc.example`。

#### 4. 配置数据库

**项目内置PostgreSQL管理**:

```bash
# 启动项目内置 PostgreSQL (数据存储在项目 .postgresql 目录)
./scripts/db_control.sh start
```

脚本会自动:
- 初始化 PostgreSQL 数据目录 (`.postgresql/data`)
- 创建 Unix socket 目录 (`.postgresql/run`)
- 创建数据库 `mul_in_one`
- 运行 Alembic 数据库迁移

**使用外部PostgreSQL**:

如果您已有PostgreSQL实例,可通过环境变量配置:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"
```

**数据库位置说明**:
- 项目内置方式: 所有数据存储在项目的 `.postgresql/` 目录下
- 可移植性: 整个项目目录可以迁移到不同机器,无需重新配置
- Unix Socket: 使用项目相对路径,避免权限和路径问题

#### 5. 启动 Milvus

**使用项目脚本** (推荐):

```bash
# 首次启动前，确保已加载环境变量
direnv allow  # 或 source .envrc

# 使用项目控制脚本启动 Milvus
./scripts/milvus_control.sh start

# 查看 Milvus 状态
./scripts/milvus_control.sh status

# 查看 Milvus 日志
./scripts/milvus_control.sh logs
```

**手动启动** (不推荐，需要手动设置环境变量):

```bash
# 确保环境变量已设置
export DOCKER_VOLUME_DIRECTORY="$(pwd)/external/NeMo-Agent-Toolkit/examples/deploy"
export MILVUS_CONFIG_DIR="$(pwd)/configs"
export MILVUS_MEM_LIMIT="6g"

# 使用 Docker Compose 启动
docker compose -f configs/docker-compose.milvus.local.yml up -d

# 查看日志
docker compose -f configs/docker-compose.milvus.local.yml logs milvus-standalone --tail=200
```

**验证连接**:

```bash
# 测试 Milvus 端口是否可达
nc -vz localhost 19530

# 查看配置文件是否正确挂载
docker compose -f configs/docker-compose.milvus.local.yml run --rm milvus ls -l /milvus/configs
```

**数据持久化**: 
- Milvus 数据存储在 `external/NeMo-Agent-Toolkit/examples/deploy/volumes/` 目录
- 配置文件从 `configs/milvus.yaml` 挂载
- 支持项目整体迁移

#### 6. 启动后端服务

```bash
# 方式 1: 使用启动脚本 (推荐)
./scripts/start_backend.sh

# 方式 2: 手动启动
cd /home/lonnet/Developers/Mul_in_ONE
uv run uvicorn mul_in_one_nemo.service.app:create_app \
  --factory \
  --reload \
  --host 0.0.0.0 \
  --port 8000 \
  --reload-exclude "external/*" \
  --reload-exclude ".postgresql/*"
```

后端将在 `http://localhost:8000` 运行

- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **健康检查**: http://localhost:8000/health

#### 7. 启动前端应用

```bash
# 进入前端目录
cd src/mio_frontend/mio-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 运行

> 若需要 OAuth 登录，请确保 `.envrc` 中的 `FRONTEND_URL` 与实际前端地址一致（开发默认 `http://localhost:5173`）。

#### 8. 初始化配置

1. **访问 Web 界面**: 打开 http://localhost:5173
2. **创建 API Profile**: 导航到 "API Profiles" 页面
   - 创建 LLM API 配置 (如 DeepSeek, GPT-4 等)
   - 创建 Embedding API 配置 (如 BAAI/bge-large-zh-v1.5)
3. **配置全局 Embedding**: 在 "Personas" 页面顶部配置租户级 embedding 模型
4. **创建 Persona**: 添加 AI 人格,设置名称、handle、语气、背景等
5. **开始对话**: 在 "Sessions" 页面创建新会话,选择 Target Agents 开始聊天!

#### 9. 工具优先（NAT）配置与行为
- **已注册工具**: `WebSearch` 与 `RagQuery`
- **调用方式**: LLM 在对话过程中按需通过函数调用触发工具,无需用户使用内联触发器
- **工具实现**:
  - `WebSearch`: 自包含实现（内置 DuckDuckGo 搜索和页面抓取）
  - `RagQuery`: 调用 RAGService 进行向量检索
- **RAG 行为**: 完全按需检索，无预注入。LLM 通过 `RagQuery` 工具主动获取背景片段
- **代码位置**:
  - `src/mul_in_one_nemo/tools/web_search_tool.py`（完整工具实现）
  - `src/mul_in_one_nemo/tools/rag_query_tool.py`（工具封装）
  - `src/mul_in_one_nemo/runtime.py`（工具注册与运行时绑定）
- **详细设计**: 参见 [系统架构设计文档](docs/architecture.md) 的"工具模块"章节

#### 工具注册示例

在 `runtime.py` 中，工具通过 NAT 的 builder 注册并暴露给 LLM 函数调用接口：

```python
# src/mul_in_one_nemo/runtime.py
from mul_in_one_nemo.tools.web_search_tool import web_search_tool
from mul_in_one_nemo.tools.rag_query_tool import rag_query_tool

class MultiAgentRuntime:
    def __init__(self):
        self.builder = WorkflowBuilder()
        
        # 注册默认 LLM
        self.builder.set_default_llm(default_llm)
        
        # 注册通用工具（所有 Persona 可用）
        self.builder.register(web_search_tool)
        self.builder.register(rag_query_tool)
        
        # 注册 Persona 对话函数
        # ...
```

这样 LLM 在推理时可以自动发现并调用 `web_search` 和 `rag_query` 函数。

## 💡 使用指南

### Web 界面功能

#### 1. 会话管理 (Sessions)
- **创建会话**: 点击 "NEW SESSION" 按钮创建新对话
- **会话列表**: 查看所有历史会话,显示最后活动时间
- **进入对话**: 点击会话卡片进入对话界面
- **删除会话**: 删除不需要的对话记录

#### 2. Persona 管理
- **创建 Persona**: 
  - 填写名称(如"丰川祥子")、Handle(如"Saki")
  - 设置语气、主动性(0-1)、记忆窗口、最大回合数
  - 可选填写背景传记(将自动转为 RAG 知识库)
  - 绑定 LLM API Profile
- **编辑 Persona**: 修改现有人格配置
- **刷新背景**: 手动触发背景知识重新摄取
- **设为默认**: 标记默认参与的 Persona

#### 3. API Profile 管理
- **创建 API 配置**:
  - 名称: 配置的显示名称
  - Base URL: API 端点地址
  - Model: 模型名称(如 `deepseek-chat`, `BAAI/bge-large-zh-v1.5`)
  - API Key: 认证密钥(加密存储)
  - Temperature: 温度参数(可选)
- **用途分类**:
  - LLM 配置: 用于 Persona 对话生成
  - Embedding 配置: 用于全局向量化(RAG)

#### 4. 全局 Embedding 配置
- **位置**: Personas 页面顶部黄色配置面板
- **作用**: 所有 Persona 的背景知识统一使用此 embedding 模型
- **推荐模型**: 
  - 中文: `BAAI/bge-large-zh-v1.5`
  - 英文: `text-embedding-ada-002`
  - 多语言: `BAAI/bge-m3`

#### 5. 对话功能
- **选择 Target Agents**: 指定参与对话的 Persona(可多选)
- **发送消息**: 输入文本后按 Enter 或点击发送按钮
- **实时响应**: Agent 回复以流式方式逐字显示
- **用户 Persona**: 点击右上角徽章图标设置用户角色扮演人格
- **消息反馈**: 对 Agent 回复进行点赞/点踩(预留功能)

#### 6. DEBUG 日志
- **查看日志**: 实时查看后端操作日志
- **日志类型**: Milvus 操作、数据库事务、RAG 摄取等
- **自动刷新**: 每 2 秒自动更新
- **行数控制**: 选择显示最近 200/500/1000/2000 行

#### 7. 账户设置
- **资料概览**: 查看邮箱、用户名、角色、验证状态等账户信息
- **危险操作**: 通过 Account Settings 页面中的“Danger Zone” 执行账号删除，需输入 `DELETE` 二次确认
- **安全联动**: 删除成功后自动登出并清理本地 token，确保数据彻底移除

### API 使用示例

#### 注册并通过 Turnstile 验证

```bash
curl -X POST "http://localhost:8000/api/auth/register-with-captcha" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123!",
    "username": "tester",
    "display_name": "Test User",
    "turnstile_token": "1x0000000000000000000000000000000AA"
  }'
```

> 如果关闭 Turnstile（默认禁用），`turnstile_token` 可省略；开启后必须提供前端 widget 返回的 token。

#### 创建会话

```bash
curl -X POST "http://localhost:8000/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "default_tenant",
    "user_persona": "我是一个对 AI 技术充满好奇的开发者"
  }'
```

#### 发送消息

```bash
curl -X POST "http://localhost:8000/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "大家好,今天聊什么？",
    "target_personas": ["Saki", "Uika"]
  }'
```

#### WebSocket 监听响应

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/sessions/{session_id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.event, data.data);
};
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_service_persona_routes.py

# 查看覆盖率
pytest --cov=mul_in_one_nemo

# 运行并生成 HTML 报告
pytest --cov=mul_in_one_nemo --cov-report=html
```

## 🛠️ 开发指南

### 添加新的数据库迁移

```bash
# 修改 src/mul_in_one_nemo/db/models.py 后生成迁移
alembic revision --autogenerate -m "描述你的修改"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 添加新的 API 端点

1. 在 `src/mul_in_one_nemo/service/routers/` 创建或修改路由文件
2. 在 `src/mul_in_one_nemo/service/app.py` 注册路由
3. 添加对应的 Repository 方法(如需数据库操作)
4. 编写测试用例

### 前端开发

```bash
cd src/mio_frontend/mio-frontend

# 开发模式
npm run dev

# 类型检查
npm run type-check

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 🐛 故障排查

### 常见问题

**1. 数据库连接失败**
```bash
# 检查 PostgreSQL 是否运行
./scripts/db_control.sh status

# 检查数据库 URL 配置
echo $DATABASE_URL
```

**2. Milvus 连接失败**
```bash
# 检查环境变量是否正确设置
echo $DOCKER_VOLUME_DIRECTORY
echo $MILVUS_CONFIG_DIR
echo $MILVUS_MEM_LIMIT

# 检查 Milvus 容器状态
docker compose -f configs/docker-compose.milvus.local.yml ps

# 查看 Milvus 日志
./scripts/milvus_control.sh logs

# 重启 Milvus（会自动加载环境变量）
./scripts/milvus_control.sh restart

# 验证端口连通性
nc -vz localhost 19530
```

> ⚠️ **常见问题**: 如果直接使用 `docker compose` 命令失败，可能是因为 `DOCKER_VOLUME_DIRECTORY` 未设置。请使用 `./scripts/milvus_control.sh` 脚本，它会自动处理环境变量。

**3. RAG 摄取失败**
- 检查 DEBUG 页面日志查看详细错误
- 确认已配置全局 Embedding 模型
- 验证 Embedding API Profile 的模型支持 embedding 功能
- 检查 Milvus 内存使用情况 

**4. Agent 不按预期发言**
- 检查 Target Agents 是否正确选择
- 查看 Persona 的主动性(proactivity)设置
- 确认 Persona 的 API Profile 配置正确

**5. 前端无法连接后端**
- 确认后端服务运行在 `http://localhost:8000`
- 检查浏览器控制台是否有 CORS 错误
- 验证 API 端点路径是否正确

## 📅 项目状态与路线图

### ✅ 已完成功能

#### 核心对话系统
- ✅ 多智能体动态调度算法
- ✅ 基于主动性和上下文的智能发言选择
- ✅ WebSocket 实时流式输出
- ✅ @ 提及机制强制 Agent 回复
- ✅ 精准 Target Agents 控制
- ✅ 用户 Persona 角色扮演支持
- ✅ 多轮连续对话
- ✅ 对话记忆管理
 - ✅ NAT 工具优先（WebSearch、RagQuery 已注册并在运行时可发现）

#### RAG 知识增强
- ✅ 租户级全局 Embedding 配置
- ✅ Persona 背景自动向量化
- ✅ Milvus 向量存储和检索
- ✅ 文本分块和 chunk 管理
- ✅ 手动刷新背景知识
- ✅ 增删改 Persona 自动同步向量库
 - ✅ 工具化按需检索（移除每轮预注入,由 `RagQuery` 触发）

#### 数据持久化
- ✅ PostgreSQL 异步 ORM
- ✅ Alembic 数据库迁移管理
- ✅ 会话和消息历史存储
- ✅ Persona 动态配置管理
- ✅ API Profile 加密存储
- ✅ 多租户支持

#### Web 应用界面
- ✅ 会话列表和管理
- ✅ 实时对话界面
- ✅ Persona CRUD 操作
- ✅ API Profile 管理
- ✅ 全局 Embedding 配置面板
- ✅ DEBUG 日志查看器
- ✅ 响应式 UI 设计

#### 开发者工具
- ✅ FastAPI Swagger 文档
- ✅ 热重载开发模式
- ✅ 单元测试和集成测试
- ✅ Docker 支持 (Milvus)
- ✅ 辅助脚本集合
 - ✅ NAT 工具注册与运行时绑定

### 🚧 进行中 / 计划中

#### 短期计划
- [ ] **Session 级长期记忆 (Long-term Memory)**
  - 为每个 Session 绑定独立的 RAG 知识库，该Session中绑定的所有Agent均可访问该知识库
  - 当对话上下文长度达到阈值时(用户可配置),异步将久远上下文压入 Session-RAG
  - 压入比例可配置(如压入最早的 1/2、1/3 或自定义比例的历史对话)
  - Session-RAG 检索优先级最低(低于 Persona 背景 RAG)
  - 实现对话历史的长期保存和智能召回,突破 memory_window 限制
- [ ] **可选的技术视图 (Tool Call Tracing)**
  - 为消息添加可选的"来源详情"展示
  - 支持查看工具调用记录(如 RagQuery 检索来源、WebSearch 链接)
  - 提供"角色扮演模式"与"审计模式"切换,前者隐藏技术细节保持沉浸感
  - 开发场景下支持完整的工具调用链路追踪
- [ ] 消息反馈系统完善(点赞/点踩统计)
- [ ] 对话导出功能(Markdown/JSON)
- [ ] Persona 背景支持 URL 摄取
- [ ] 多文件附件上传支持
- [ ] 会话搜索和过滤

#### 中期计划
- [ ] 用户认证和权限管理
- [ ] 多租户完整隔离
- [ ] Persona 导入/导出
- [ ] 对话模板系统
- [ ] Agent 行为分析面板
- [ ] 性能监控和指标

#### 长期愿景
- [ ] 移动端应用 (React Native)
- [ ] 语音对话支持
- [ ] 图片理解和生成
- [ ] Agent 自定义工具调用
- [ ] 插件系统

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出功能建议!

### 提交 Issue
- 使用清晰的标题描述问题
- 提供复现步骤
- 附上相关日志或截图
- 说明你的环境(OS、Python 版本等)

### 提交 Pull Request
1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 代码规范
- Python: 遵循 PEP 8,使用 `ruff` 进行 linting
- TypeScript/Vue: 遵循 ESLint 配置
- 提交信息: 使用语义化提交规范

## 📄 许可证

- 本项目以 [GPLv3](LICENSE) 授权发布。
- 仓库中的第三方子模块与依赖（如 `external/NeMo-Agent-Toolkit`）保留其原始许可证，仍按各自许可证分发。

## 🙏 致谢

- [NVIDIA NeMo Agent Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) - 核心对话引擎
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [Quasar Framework](https://quasar.dev/) - Vue.js UI 组件库
- [Milvus](https://milvus.io/) - 开源向量数据库
- [LangChain](https://www.langchain.com/) - LLM 应用开发框架

## 📧 联系方式

- **项目主页**: https://github.com/KirisameLonnet/Mul_in_ONE
- **问题反馈**: https://github.com/KirisameLonnet/Mul_in_ONE/issues
- **作者**: KirisameLonnet

---

**如果这个项目对你有帮助,请给个 ⭐ Star 支持一下!**
