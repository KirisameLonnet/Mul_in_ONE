# Mul-in-One Frontend

**多智能体对话系统的前端应用**

## 技术栈

- **框架**: Vue 3 (Composition API)
- **UI 组件**: Quasar Framework
- **构建工具**: Vite
- **语言**: TypeScript
- **状态管理**: Vue Composition API
- **通信**: Axios (REST API) + WebSocket (实时消息)

## 核心功能

- ✅ 用户认证与账号隔离支持
- ✅ 会话管理（创建、列表、详情）
- ✅ 实时对话（WebSocket 流式消息）
- ✅ Persona 管理（创建、编辑、删除）
  - 支持背景经历字段（无字数限制）
  - API Profile 绑定
  - 记忆窗口与回合限制配置
- ✅ API Profile 管理（LLM 配置）
- ✅ 邮箱验证与注册流程（Turnstile 可选）
- ✅ 账户设置与自助注销
- ✅ 管理员用户管理（重置密码/删除账号）
- 🔄 RAG 知识库管理界面（规划中）

## 项目结构

```
src/
├── api.ts              # REST API 客户端
├── websocket.ts        # WebSocket 客户端
├── router/             # Vue Router 配置
├── composables/        # 组合式函数（如 useChat）
├── pages/              # 页面组件
│   ├── LoginPage.vue
│   ├── RegisterPage.vue
│   ├── VerifyEmailPage.vue
│   ├── SessionsPage.vue
│   ├── ChatConversationPage.vue
│   ├── PersonasPage.vue
│   └── ApiProfilesPage.vue
│   ├── AccountSettingsPage.vue
│   ├── AdminUsersPage.vue
└── assets/             # 静态资源
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 开发服务器

```bash
npm run dev
```

访问 `http://localhost:5173`（或 Vite 分配的端口）。

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 环境配置

前端默认连接到 `http://localhost:8000` 的后端 API。如需修改，请在 `src/api.ts` 中调整 `baseURL`。

若启用 Cloudflare Turnstile，请在 `.env` 中设置 `VITE_TURNSTILE_SITE_KEY`，否则前端会自动跳过验证码组件。

## API 对接

所有 API 调用已封装在 `src/api.ts` 中，包括：

- **认证**: `login()`
- **会话**: `createSession()`, `getSession()`, `getSessions()`
- **消息**: `sendMessage()`（通过 WebSocket 在 `websocket.ts`）
- **Personas**: `createPersona()`, `updatePersona()`, `deletePersona()`, `listPersonas()`
- **API Profiles**: CRUD 操作
- **RAG**: `ingestUrl()`, `ingestText()`（已定义接口，待前端 UI 集成）

## WebSocket 消息格式

实时对话使用 WebSocket，消息格式遵循 SSE 风格：

```
event: agent.start
data: {"agent": "PersonaName"}

event: agent.chunk
data: {"content": "partial text"}

event: agent.end
data: {"content": "complete message"}
```

详见 `src/composables/useChat.ts` 中的消息解析逻辑。

## 相关文档

- [项目主 README](../../../README.md)
- [架构设计文档](../../../docs/architecture.md)
- [后端 API 文档](http://localhost:8000/docs)（后端服务运行时可访问）

---

基于 Vue 3 + TypeScript + Vite 模板构建。了解更多：[Vue 3 文档](https://vuejs.org/)。
