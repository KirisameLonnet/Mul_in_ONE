# Mul-in-One (MIO) - 多智能体对话系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)](https://vuejs.org/)

**一个功能完整的多智能体对话系统,支持动态 Persona 管理、RAG 知识增强、实时流式对话和 Web 可视化界面。**

本项目基于 NVIDIA NeMo Agent Toolkit 构建,提供了从命令行工具到 Web 应用的完整解决方案,让多个 AI Agent 能够像真人群聊一样进行自然、流畅的对话互动。

## ✨ 核心特性

### 🎭 智能 Persona 系统
- **动态配置管理**: 通过 Web 界面实时创建、编辑和删除 AI 人格
- **多维度人格设置**: 支持名称、handle、语气、主动性、记忆窗口等细粒度配置
- **背景知识库**: 为每个 Persona 配置背景传记,通过 RAG 自动转换为向量知识库
- **灵活 API 绑定**: 每个 Persona 可绑定不同的 LLM API 配置(模型、温度参数等)

### 🧠 RAG 知识增强系统
- **全局 Embedding 配置**: 租户级别的统一 embedding 模型配置
- **自动向量化**: 创建或更新 Persona 背景时自动分块、向量化并存储到 Milvus
- **智能检索增强**: 对话时自动检索相关背景知识,提升回复质量和准确性
- **手动刷新控制**: 支持主动触发背景知识的重新摄取和索引

### 💬 高级对话功能
- **动态调度算法**: 基于主动性、上下文和话题相关性智能选择发言者
- **精准 Target 控制**: 用户可明确指定参与对话的 Agent,避免无关干扰
- **实时流式输出**: WebSocket 推送,逐字展示 Agent 回复过程
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

### 🔧 开发者友好
- **RESTful API**: 完整的 FastAPI 后端,支持 Swagger 文档
- **数据库持久化**: PostgreSQL + Alembic 版本控制
- **向量数据库**: Milvus 高性能向量检索
- **命令行工具**: 无需 Web 界面的快速测试方式
- **热重载开发**: 前后端均支持代码修改后自动重载

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI (异步 Web 框架)
- **ORM**: SQLAlchemy 2.0 (async)
- **数据库**: PostgreSQL
- **向量数据库**: Milvus
- **对话引擎**: NVIDIA NeMo Agent Toolkit
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

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** - 推荐的 Python 包管理器
- **Node.js 18+** 和 npm
- **PostgreSQL 14+**
- **Milvus** - 向量数据库 (推荐使用 Docker)
- **Docker** (可选,用于运行 Milvus)

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/KirisameLonnet/Mul_in_ONE.git
cd Mul_in_ONE
```

#### 2. 初始化后端

```bash
# 创建并激活 Python 虚拟环境
uv venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 运行引导脚本 (自动克隆 NeMo Toolkit 并安装所有依赖)
./scripts/bootstrap_toolkit.sh
```

#### 3. 配置数据库

```bash
# 启动 PostgreSQL
./scripts/db_control.sh start

# 运行数据库迁移
alembic upgrade head
```

**数据库配置**: 默认使用 `postgresql+asyncpg://postgres:postgres@localhost:5432/mul_in_one`

可通过环境变量 `DATABASE_URL` 自定义:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"
```

#### 4. 启动 Milvus

```bash
# 使用 Docker 启动 Milvus
./scripts/milvus_control.sh start

# 或手动启动
docker run -d --name milvus-standalone \
  -p 19530:19530 -p 9091:9091 \
  -e ETCD_USE_EMBED=true \
  -v $(pwd)/.milvus:/var/lib/milvus \
  milvusdb/milvus:latest
```

#### 5. 启动后端服务

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

#### 6. 启动前端应用

```bash
# 进入前端目录
cd src/mio_frontend/mio-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 运行

### 7. 初始化配置

1. **访问 Web 界面**: 打开 http://localhost:5173
2. **创建 API Profile**: 导航到 "API Profiles" 页面
   - 创建 LLM API 配置 (如 DeepSeek, GPT-4 等)
   - 创建 Embedding API 配置 (如 BAAI/bge-large-zh-v1.5)
3. **配置全局 Embedding**: 在 "Personas" 页面顶部配置租户级 embedding 模型
4. **创建 Persona**: 添加 AI 人格,设置名称、handle、语气、背景等
5. **开始对话**: 在 "Sessions" 页面创建新会话,选择 Target Agents 开始聊天!

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

### 命令行工具 (CLI)

```bash
# 交互式对话 (流式输出)
uv run mul-in-one-nemo --stream

# 单次对话测试
uv run mul-in-one-nemo --message "你好,大家！"

# 查看帮助
uv run mul-in-one-nemo --help
```

### API 使用示例

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
# 检查 Milvus 容器状态
docker ps | grep milvus

# 查看 Milvus 日志
docker logs milvus-standalone

# 重启 Milvus
./scripts/milvus_control.sh restart
```

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

#### RAG 知识增强
- ✅ 租户级全局 Embedding 配置
- ✅ Persona 背景自动向量化
- ✅ Milvus 向量存储和检索
- ✅ 文本分块和 chunk 管理
- ✅ 手动刷新背景知识
- ✅ 增删改 Persona 自动同步向量库

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
- ✅ 命令行工具 (CLI)
- ✅ 热重载开发模式
- ✅ 单元测试和集成测试
- ✅ Docker 支持 (Milvus)
- ✅ 辅助脚本集合

### 🚧 进行中 / 计划中

#### 短期计划
- [ ] **Session 级长期记忆 (Long-term Memory)**
  - 为每个 Session 绑定独立的 RAG 知识库，该Session中绑定的所有Agent均可访问该知识库
  - 当对话上下文长度达到阈值时(用户可配置),异步将久远上下文压入 Session-RAG
  - 压入比例可配置(如压入最早的 1/2、1/3 或自定义比例的历史对话)
  - Session-RAG 检索优先级最低(低于 Persona 背景 RAG)
  - 实现对话历史的长期保存和智能召回,突破 memory_window 限制
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

本项目采用 [MIT License](LICENSE) 开源协议。

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
