# 迁移计划：采用 NAT 官方方案实现多租户 RAG

目标：从当前代码式工具注册与服务层封装的方案，平滑迁移到完全符合 NeMo Agent Toolkit（NAT）官方标准/接口的实现路径，使用 NAT 内置 `milvus_retriever` + `nat_retriever` 组件，并在此基础上实现多租户与多 Persona 的动态检索能力。

## 范围与原则
- 覆盖 RAG 的检索层（Retriever）、工具层（Tool）、流程层（Workflow）及 API 层（FastAPI/Service）。
- 优先使用 NAT 内置组件与 YAML 声明式配置；保留必要的适配层用于多租户的运行时参数注入。
- 逐步迁移，保证现有功能在迁移过程中可用；对外 API（路由与请求/响应）保持兼容。

## 现状回顾（当前架构）
- 工具层：`rag_query_tool.py` 通过 `@register_function` 直接调用 `RAGService.retrieve_documents()`。
- 服务层：`RAGService` 管理 Milvus 连接、集合命名（多租户/多 Persona）、嵌入模型解析（从数据库配置）、摄取与删除逻辑。
- 文档摄取：`ingest_url()`/`ingest_text()` 在服务层执行，落到相应租户/Persona 的集合。
- 多租户：集合命名约定 `"{tenant_id}_persona_{persona_id}_rag"`；嵌入模型/API Key 来自 DB。

## 目标架构（NAT 官方模式 + 多租户）
NAT 三层：
- 底层检索：`MilvusRetriever`（内置），支持同步/异步客户端与 Embeddings。
- 工具包装：`nat_retriever`（内置），将任意 retriever 暴露为工具，LLM 可调用。
- 声明式配置：YAML 定义 `retrievers` / `functions` / `workflow` / `embedders`。

在此基础上实现多租户：
- 运行时适配器：在工具调用前解析 `tenant_id`/`persona_id`，动态计算 `collection_name` 与 Embeddings；将这些绑定到 `MilvusRetriever` 实例或其 `search()` 参数中。
- 仍保留摄取/删除等业务逻辑在服务层，但内部优先使用 NAT 的 Retriever 模式统一检索接口。

## 分阶段迁移计划

### 阶段 1：引入 NAT YAML + 基础 retriever/tool
1. 新增 NAT workflow 配置文件：`configs/rag_multi_tenant.yml`
   - `retrievers.tenant_milvus`：`_type: milvus_retriever`，配置 Milvus URI 与默认 embedder 引用（可在运行时覆盖）。
   - `functions.rag_retriever_tool`：`_type: nat_retriever`，引用上面 retriever，提供工具描述。
   - `embedders.milvus_embedder`：默认 embedder（例如 NIM 模型），作为兜底。
   - `workflow.react_agent`：包含 `rag_retriever_tool`。

2. 在后端启动流程中加载该 YAML，确保 `Builder` 能够构建 retriever 与工具。

3. 保持现有 `RAGService` 未改动，开始编写适配器以便在调用 `nat_retriever` 时传入动态参数。

### 阶段 2：多租户运行时适配
1. 适配器职责：
   - 解析请求中的 `tenant_id`、`persona_id`；根据命名约定生成 `collection_name`。
   - 从 DB 查找该租户/Persona 的嵌入模型信息（模型名/Key/Endpoint）；构造对应 `Embeddings`。
   - 将 embedder 注入 retriever（重新构建或替换 retriever 的 embedder），并以 `search(query, collection_name, top_k, filters)` 调用。

2. 设计两种绑定方式：
  - 推荐：方式 A（运行时重建）：每次请求新建一个轻量的 `MilvusRetriever(client, tenant_embedder)`，直接传入 `collection_name`/`top_k`。Python 对象创建开销极低，且避免并发修改同一实例状态导致的跨租户数据泄露。
  - 不推荐：方式 B（共享实例绑定）：在高并发下对同一 retriever 实例绑定不同集合名存在竞态与泄露风险，应避免。

3. 在 `RAGService.retrieve_documents()` 内部切换到使用 NAT 的 `MilvusRetriever`，统一返回 `RetrieverOutput` 或转换为现有 `Document` 格式以保持兼容。

### 阶段 3：工具层与 `rag_query_tool.py` 对齐
1. 更新 `rag_query_tool.py` 以调用 `nat_retriever` 的客户端：
  - 保留输入 schema 仅包含 `query` 与可选 `top_k`，不向 LLM 暴露 `tenant_id`/`persona_id`。
  - 在工具实现内部（或服务层）从 FastAPI Request/Session Context 隐式获取 `tenant_id`/`persona_id`，然后调用适配器完成 retriever 的创建与 `search()` 执行。
   - 输出保持为 `passages(text, source)` 以兼容前端/路由。

2. 或者：直接使用 YAML 中的 `nat_retriever` 生成的工具，由系统提示指导 LLM 在需要时调用；我们通过会话上下文将 `tenant_id`/`persona_id` 注入（例如通过工具参数扩展或会话绑定）。

### 阶段 4：摄取/删除逻辑接入 NAT 客户端
1. 摄取：
   - 解析 URL/文本，分割为 chunk，生成 embeddings（使用租户 embedder）。
   - 连接 Milvus，向 `{tenant}_{persona}_rag` 集合写入（保持 schema 与向量字段一致）。
   - 可复用现有分割与存储流程，但推荐将写入使用统一的 Milvus 客户端与 schema 管理。

2. 删除：
   - 基于 `source` 或 `document_id` 在指定集合删除。

3. 健康检查：
   - 服务层统一管理 Milvus 连接，提供 ping/describe 集合等 API。

## 配置示例（草案）
文件：`external/NeMo-Agent-Toolkit/examples/RAG/simple_rag/configs/milvus_rag_config.yml` 为参考；本项目建议：`configs/rag_multi_tenant.yml`

```yaml
retrievers:
  tenant_milvus:
    _type: milvus_retriever
    uri: http://localhost:19530
    embedding_model: milvus_embedder  # 运行时可替换为租户特定 embedder
    top_k: 5

functions:
  rag_retriever_tool:
    _type: nat_retriever
    retriever: tenant_milvus
    description: Retrieve multi-tenant persona RAG chunks

llms:
  nim_llm:
    _type: nim
    model_name: meta/llama-3.3-70b-instruct
    temperature: 0
    max_tokens: 4096
    top_p: 1

embedders:
  milvus_embedder:
    _type: nim
    model_name: nvidia/nv-embedqa-e5-v5
    truncate: END

workflow:
  _type: react_agent
  tool_names:
   - rag_retriever_tool
  verbose: true
  llm_name: nim_llm
```

## 代码适配器示例（草案接口）
位置建议：`src/mul_in_one_nemo/service/rag_adapter.py`

```python
from nat.retriever.milvus.retriever import MilvusRetriever
from pymilvus import MilvusClient

class RagAdapter:
    def __init__(self, client: MilvusClient, embedder_factory):
        self.client = client
        self.embedder_factory = embedder_factory  # 根据租户配置返回 Embeddings

    async def search(self, tenant_id: int, persona_id: int, query: str, top_k: int = 5):
        collection_name = f"{tenant_id}_persona_{persona_id}_rag"
        embedder = await self.embedder_factory(tenant_id, persona_id)
        retriever = MilvusRetriever(client=self.client, embedder=embedder)
        return await retriever.search(query=query, collection_name=collection_name, top_k=top_k)
```

在现有 `RAGService.retrieve_documents()` 中使用 `RagAdapter`，将返回结果转换为现有的输出模型（如 `Document`/`RagPassage`）。

## API 层（FastAPI）对齐要点
- 路由携带 `tenant_id`、`persona_id`、`query`、`top_k`；其中 `tenant_id`/`persona_id` 仅用于服务层，不进入工具的公开 schema。
- 工具调用时由服务层/工具实现从 Request/Session Context 隐式注入 `tenant_id`、`persona_id`，避免在 LLM 可见参数中出现系统元数据。
- 服务层在处理时调用 `RagAdapter.search()` 并封装响应；摄取路由同样携带 `tenant_id`、`persona_id`，统一落库。

## 测试与验证
- 单元测试：
  - 集合命名生成与边界条件（空/负数/超大 ID）。
  - 不同租户的 embedder 配置解析与绑定。
  - `search()` 在集合不存在时抛错与处理（`CollectionNotFoundError`）。

- 集成测试：
  - 两个不同租户/Persona 的摄取与查询，结果隔离验证。
  - 工具调用链条（LLM → `nat_retriever` → `MilvusRetriever`）。

## 风险与缓解
- 运行时重建 retriever 带来的开销：
  - 缓解：复用 MilvusClient（或连接池）；可缓存 per-tenant embedder 实例。`MilvusRetriever` 作为轻量对象每请求重建可确保线程安全与租户隔离。
- YAML 与代码式注册共存：
  - 缓解：逐步迁移；工具入口统一走 NAT 的 `nat_retriever`。
- 租户配置缺失或不合法：
  - 缓解：显式报错与可观测性日志；提供默认 embedder 兜底。
- 异步与同步接口兼容：
  - 缓解：优先使用 NAT 的异步路径（`MilvusRetriever` 会检测 async 客户端并使用 `await`）。如遇同步阻塞组件，在 FastAPI 中通过 `run_in_executor` 包裹调用，确保不阻塞事件循环。

## 里程碑
1. 完成 YAML 配置与加载（retriever/tool/workflow/embedders）。
2. 引入 `RagAdapter` 并在 `RAGService` 内部切换到 NAT 检索。
3. 路由与工具层联调，支持多租户查询。
4. 摄取/删除逻辑接入 NAT 客户端；完成端到端验证。
5. 文档与示例更新；提供运行脚本与试用命令。

## 快速试用命令（zsh）
```zsh
# 启动后端（如需）
python scripts/start_backend.sh

# 查询：租户1 / persona 42
curl -s 'http://localhost:8000/rag/query' \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":1,"persona_id":42,"query":"CUDA streams","top_k":5}'

# 查询：租户2 / persona 7
curl -s 'http://localhost:8000/rag/query' \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":2,"persona_id":7,"query":"MCP basics","top_k":5}'
```

## 结论
采用 NAT 官方 `milvus_retriever` + `nat_retriever` 方案，通过一个轻量运行时适配器实现多租户与多 Persona 的动态检索；保留现有服务层用于摄取/删除与配置解析。该设计兼顾与 NAT 的对齐与项目的灵活性，可逐步迁移且风险可控。
