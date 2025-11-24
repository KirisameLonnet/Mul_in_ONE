# Mul-in-One 多租户后端设计稿

> 当前仓库状态：`b1598f0 (HEAD -> main) 后端核心逻辑`，提交时间 `2025-11-20 02:15:58 +0800`。
> 设计稿撰写日期：2025-11-20。

## 1. 设计目标
- 在不破坏现有 CLI runtime 的前提下，提供 REST + WebSocket 接口，服务多租户、多会话并发。
- 阶段 1-2 仅依赖单进程 FastAPI + asyncio，利用 sticky session 控制会话并发；阶段 3+ 可平滑扩展到队列 + Worker。
- 强制租户级数据隔离，确保配额、鉴权、审计可追踪。
- 便于运维：配置集中化、可观测性、可滚动升级。

## 2. 服务分层
| 层级 | 责任 | 关键模块（建议路径） |
| --- | --- | --- |
| API 层 | REST/WS 接口、鉴权、输入校验 | `src/mul_in_one_nemo/service/api.py`, `routers/sessions.py`, `routers/personas.py` |
| Session/Orchestrator 层 | 维护 `SessionContext`、调度 runtime、粘性路由 | `service/session_service.py`, `service/runtime_manager.py` |
| Domain 层 | Persona、Memory、Scheduler、Runtime | 复用现有 `persona.py`, `memory.py`, `scheduler.py`, `runtime.py`（逐步接口化） |
| Infra 层 | 存储、配置、日志、外部依赖 | `infrastructure/settings.py`, `repositories/*.py`, `clients/*.py` |

## 3. 请求生命周期（阶段 1-2）
1. **Auth**：FastAPI 依赖解析 JWT，生成 `TenantContext`（tenant_id、user_id、roles、quota_limits）。
2. **路由**：`/api/sessions/{session_id}/messages` 保存用户输入至 Postgres（会话/消息表）+ Redis（最近 turns）。
3. **排队**：该 session 的 ID 被推入进程内 `asyncio.Queue`，并根据 session_id hash 找到对应的 `RuntimeSession`。
4. **执行**：`RuntimeSession` 获取 `asyncio.Lock`，从 Memory Store 拉取历史，构建 persona prompts，调用 `runtime.invoke_stream`。
5. **回传**：运行结果以事件（chunk/turn_completed/errors）形式推送到 WebSocket；REST 调用返回 ack + `stream_channel`。
6. **后处理**：写入长存储（Postgres/向量库）、更新 scheduler state、打点监控。
7. **粘性维护**：若 FastAPI 进程内缓存命中，直接复用现有 `RuntimeSession`；若 miss，则按 session_id hash 新建实例并注册到 `RuntimeManager`，同时将该映射写入 Redis 以便多副本部署时可追踪。

## 4. API 概要
### REST
| 方法 | 路径 | 描述 |
| --- | --- | --- |
| `POST` | `/api/sessions` | 创建会话，返回 `session_id`、缺省 persona 集合、WebSocket token。 |
| `GET` | `/api/sessions/{id}` | 查询会话元数据、活跃 persona、最近消息。 |
| `POST` | `/api/sessions/{id}/messages` | 发送用户消息，可选择 `target_personas`，返回消息 ID 与 WebSocket channel。 |
| `GET` | `/api/personas` | 列出租户可用 persona（含 overrides）。 |
| `POST` | `/api/personas/{id}/overrides` | 写入用户自定义参数（temperature、proactivity 等）。 |

示例：

```http
POST /api/sessions/{id}/messages
Authorization: Bearer <JWT>
Content-Type: application/json

{
   "content": "@chef 来个今天菜单",
   "target_personas": ["chef"],
   "metadata": {"language": "zh", "priority": "high"}
}
```

```json
// 202 Accepted
{
   "message_id": "msg_01HXYZ",
   "session_id": "sess_01HABC",
   "stream_channel": "ws://.../ws/sessions/sess_01HABC?token=..."
}
```

### WebSocket（`/ws/sessions/{id}`）事件
- `session.accepted`: 服务器确认连接与粘性绑定。
- `agent.chunk`: persona 输出的流式文本片段。
- `agent.completed`: persona 完整回应（含 tokens、latency）。
- `scheduler.update`: 当前候选/typing 状态。
- `system.error`: 错误信息（可指导客户端重试）。

## 5. 数据模型（初稿）
| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `tenants` | `id`, `name`, `plan`, `limits` | 基础租户信息。 |
| `users` | `id`, `tenant_id`, `external_id`, `role` | 绑定身份提供者 ID。 |
| `sessions` | `id`, `tenant_id`, `user_id`, `status`, `created_at`, `persona_set` | 一次多 agent 对话的生命周期。 |
| `messages` | `id`, `session_id`, `sender_type`, `sender_id`, `content`, `meta`, `created_at` | 用户/agent 消息。 |
| `persona_overrides` | `id`, `tenant_id`, `persona_id`, `config_json`, `updated_at` | 用户/租户对 persona 的动态配置。 |
| `quotas` | `tenant_id`, `window`, `tokens_used`, `budget_used` | 配额统计。 |
| `api_profiles` | `id`, `tenant_id`, `name`, `base_url`, `model`, `api_key_cipher`, `temperature`, `created_by`, `created_at` | 前端写入的 API 配置，`api_key_cipher` 使用应用层密钥加密后存储。 |
| `persona_bindings` | `persona_id`, `api_profile_id`, `scopes`, `updated_at` | persona 与 API profile 的动态绑定，支持不同 persona 指向不同大模型。 |

> **密钥策略**：服务端维护 `MUL_IN_ONE_KMS_KEY`（或 KMS 生成的 envelope key），使用 AES-GCM/Fernet 对 API key 做应用层加密再写入 Postgres；运行时解密仅在调用前进行，并记录审计日志。

Redis Key 建议：
- `session:{id}:lock`：`asyncio.Lock` 粘性信息（服务器内存 + Redis 兜底）。
- `session:{id}:recent`：列表，缓存最近 N 条对话。
- `scheduler:{id}`：记录 `turn_count`、`last_speaker`, `cooldown_until`。
- `ws_token:{session}:{user}`：短期 WebSocket token，支持多终端订阅。

## 6. Runtime & Scheduler 策略
- 将 `TurnScheduler` 拆成纯函数 + 状态输入，持久化只需 `turn_count`, `last_speaker`, `cooldowns`；其余状态（@mention、context tags）通过消息历史即时推导。
- `RuntimeSession` 负责：
  1. lazy 初始化 `MultiAgentRuntime`（含 persona functions）；
  2. 维护 `asyncio.Queue`，按顺序处理同一 session 的任务；
  3. 在 WebSocket 断开时取消任务，释放锁；
  4. 记录 metrics（per persona tokens, latency）。

## 7. 配置与依赖
- `api_config.py` 新增字段：
  - `auth_issuer`, `auth_audience`, `jwks_url`
  - `postgres_dsn`, `redis_url`, `object_store_url`
- `database_url`（Postgres，推荐 asyncpg 驱动）
- `redis_url`（短期记忆/锁，可与上文同源）
  - `default_quota`（tokens/minute, concurrent_sessions）
  - `feature_flags`（`enable_queue`, `enable_long_memory`）。
- `encryption_key`：用于加密 API key/Secret（Fernet/AES-GCM），不同环境使用不同密钥，可接入云 KMS。
- `.env.example` 覆盖以上变量；`Settings.from_env()` 替换 CLI-only 逻辑。

## 8. 可观测性
- 中间件：请求 ID、tenant ID 注入日志上下文。
- 指标：
  - `http_requests_total`, `ws_connections_active`
  - `runtime_tokens_total{tenant,persona}`
  - `scheduler_wait_seconds`
  - `session_active_gauge`
- Trace：`runtime.invoke_stream` -> LLM provider -> memory persist 全链路。

## 9. 迭代里程碑
1. **M1：Async API Prototype**
   - FastAPI Service + `/api/sessions`、`/api/sessions/{id}/messages` + WebSocket。
   - 内存级 SessionStore/MemoryStore，支持单用户多会话验证。
2. **M2：持久化与多租户**
   - 接入 Postgres/Redis；实现租户/用户表、`ConversationMemoryStore`、`SchedulerStateStore`。
   - JWT 鉴权、配额检查、persona overrides 接口。
3. **M3：扩展性与治理**
   - 视压测结果决定是否启用队列；补充分布式锁、重试策略。
   - 接入日志/指标/trace，完善运行手册。
4. **M4：生产硬化**
   - 安全策略、速率限制、费用统计、审计日志。

## 10. 进度记录
| 时间 | 已完成 | 下一步 |
| --- | --- | --- |
| 2025-11-20 10:00 | 形成多租户改造方案（async 优先）、完成服务分层与 API/数据模型设计 | M1：搭建 FastAPI 服务骨架，与现有 runtime 打通最小闭环 |
| 2025-11-20 16:00 | 细化生命周期、API payload 样例、Redis key 规划，补充测试策略要求 | 准备 M1 相关 FastAPI service skeleton + 文档结构测试 |
| 2025-11-20 22:30 | 完成 FastAPI 服务、SessionService 队列化、内存仓库消息写入、Stub Runtime；新增 `NemoRuntimeAdapter` 可切换至真实运行时，REST/WS API 与测试跑通 | M2：替换持久化为 Postgres/Redis，接入 JWT 鉴权与多租户配额，同时暴露历史查询 API |
| 2025-11-21 00:30 | 明确 PostgreSQL + Redis 作为持久化/队列栈，设计 API profile 加密存储、前端写入流程及完整开发路线 | 实施阶段 1：落地 Postgres schema、鉴权依赖与 API/Persona 管理接口 |
| （持续更新） |  |  |

## 11. 开放问题
- FastAPI 与 runtime 间的 persona 注册是否需要缓存刷新策略？
- 会话粘性在多实例部署时是否交由网关（如 Nginx IP Hash）还是应用内协调？
- 长记忆向量库首选 pgvector 还是独立 Milvus，取决于部署成本，需要压测后再定。

## 12. 模块接口速览
| 模块 | 关键接口 | 说明 |
| --- | --- | --- |
| `SessionService` | `create_session(ctx) -> Session`, `enqueue_message(ctx, session_id, payload)` | 负责会话生命周期与消息排队，内部落库、写 Redis、推任务到 runtime。 |
| `RuntimeManager` | `get_or_create_runtime(session_id)`, `dispatch(session_id)` | 维护 session → runtime 的粘性映射，并提供取消/超时。 |
| `ConversationMemoryStore` | `append(turn)`, `fetch(session_id, limit)` | 统一内存/Redis/Postgres 后端。 |
| `SchedulerStateStore` | `load(session_id)`, `save(session_id, state)` | 精简状态持久化，配合纯函数 scheduler。 |

## 13. 测试策略
- **覆盖范围**：
   - 文档结构：确保关键章节（目标、分层、生命周期、API、数据模型、策略、配置、可观测性、里程碑、进度、开放问题、接口速览、测试策略）存在并保持顺序。
   - 配置字段：解析 `api_config.py` 时需有对应字段单元测试。
   - Runtime 行为：M1 起写异步单元测试验证 `RuntimeSession` 粘性与序列化。
- **记录方式**：每个测试文件顶部注明编写日期和覆盖范围；CI 输出中打印 `TEST_TIMESTAMP` 方便追踪。
- **工具**：pytest + anyio（处理 async），借助 `pytest.mark.asyncio` 驱动事件循环；对 Redis/Postgres 依赖采用 `pytest` fixtures + testcontainers 或 fakeredis。

## 14. 后续开发路线（2025-11 ~ ）
1. **基础设施落地**
   - 引入 PostgreSQL（Docker Compose + Alembic 迁移），建表：`tenants`、`users`、`sessions`、`session_messages`、`api_profiles`、`persona_bindings`。
   - 接入 Redis（可选）存储短期队列/锁；完善 `.env.example`，加入 `DATABASE_URL`、`REDIS_URL`、`ENCRYPTION_KEY`。
2. **鉴权与上下文注入**
   - 实现 JWT/OIDC 校验，提供临时本地登录（开发时可使用静态 token）。
   - FastAPI 依赖将 `tenant_id`、`user_id` 注入所有 API，去掉 query 参数式的 `tenant_id`/`user_id`。
3. **API/Persona 管理接口**
   - REST CRUD：`POST /api/tenants/{id}/apis`、`POST /api/tenants/{id}/personas`、`PATCH/DELETE`，写入加密后的 API key。
   - 为普通用户屏蔽明文 API key，只返回配置状态；管理员可重新生成/撤销。
4. **运行时接入**
   - `NemoRuntimeAdapter` 根据当前 session/tenant 载入 persona + API profile，解密 key 后调用真实模型。
   - 增加运行时熔断与降级逻辑：若配置缺失或调用失败，返回明确错误并可回落到 stub（受 feature flag 控制）。
5. **会话存储迁移**
   - `SessionRepository` 切换为 Postgres 实现；内存版本保留在测试中使用。
   - 历史查询 API 改为分页，支持时间范围筛选。WebSocket 推送还需写入消息表，确保刷新后可回放。
6. **可观测性与治理**
   - 中间件注入 request_id/tenant_id 日志，Prometheus 指标（HTTP、WS、runtime tokens），OTEL trace。
   - 配置速率限制、配额告警、API 配置审计日志。
7. **前端协作**
   - 提供 Persona/API 管理界面所需的 swagger/contract；约定 secret 只写不读，使用状态字段反馈配置是否有效。

> 以上步骤完成后，即可将运行模式从回声切换到真实多模型调用，并满足持久化、鉴权、审计、安全等上线要求。
