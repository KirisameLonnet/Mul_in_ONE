# RAG (检索增强生成) 功能文档

本文档详细介绍 Mul-in-One 项目中的 RAG (Retrieval Augmented Generation) 功能，该功能用于增强 persona 的上下文处理能力，特别适用于拥有丰富背景阅历的角色。

## 1. 功能概述

RAG 功能允许为每个 persona 配置长期背景知识，这些知识在对话时会根据上下文动态检索，注入到提示词中。这解决了以下问题：

- **Token 限制**：避免将所有背景信息放入每次请求，节省 token
- **相关性**：只检索与当前话题相关的背景片段
- **一致性**：帮助角色在对话中保持背景故事的一致性
- **可扩展性**：支持非常长的背景描述（如详细的人物传记）

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      RAG Service                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Persona A   │  │ Persona B   │  │ Persona C   │         │
│  │ Knowledge   │  │ Knowledge   │  │ Knowledge   │  ...    │
│  │ Base        │  │ Base        │  │ Base        │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                          │                                   │
│                  ┌───────┴───────┐                          │
│                  │ Vector Store  │                          │
│                  │ (In-Memory /  │                          │
│                  │  Milvus)      │                          │
│                  └───────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Persona Function                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. 接收对话上下文                                      │  │
│  │ 2. 调用 RAG Service 检索相关背景                       │  │
│  │ 3. 将检索结果注入系统提示词                            │  │
│  │ 4. 调用 LLM 生成回复                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心组件

### 3.1 RAGService

中央 RAG 服务，管理所有 persona 的知识库：

```python
from mul_in_one_nemo.rag import RAGService, get_rag_service

# 获取全局 RAG 服务实例
rag_service = get_rag_service()

# 添加背景知识
rag_service.add_persona_background(
    persona_handle="historian",
    content="我在北京大学取得历史学博士学位...",
    source="academic_background"
)

# 检索相关上下文
context = rag_service.retrieve_context(
    persona_handle="historian",
    query="你的研究方向是什么？",
    k=3
)
```

### 3.2 PersonaKnowledgeBase

每个 persona 独立的知识库：

```python
from mul_in_one_nemo.rag import PersonaKnowledgeBase, InMemoryVectorStore, SimpleEmbeddings

# 创建知识库
embeddings = SimpleEmbeddings()
store = InMemoryVectorStore(embeddings)
kb = PersonaKnowledgeBase(persona_handle="chef", vector_store=store)

# 添加背景
kb.add_background(
    content="我在法国学习烹饪五年...",
    source="training_background"
)

# 检索
docs = kb.retrieve("法式甜点", k=3)
```

### 3.3 Embeddings

目前提供两种嵌入方式：

1. **SimpleEmbeddings** (默认)
   - 基于字符频率的简单嵌入
   - 无需外部 API
   - 适合开发和测试

2. **自定义 Embeddings**
   - 可接入 OpenAI、NVIDIA NIM 等嵌入服务
   - 通过 `set_rag_service()` 注入自定义服务

```python
from mul_in_one_nemo.rag import RAGService, set_rag_service
from langchain_openai import OpenAIEmbeddings

# 使用 OpenAI 嵌入
custom_service = RAGService(embeddings=OpenAIEmbeddings())
set_rag_service(custom_service)
```

## 4. 配置方式

### 4.1 YAML 配置

在 persona YAML 文件中配置 `background` 字段：

```yaml
personas:
  - name: 历史学家
    handle: historian
    prompt: 你是一位专攻中国古代史的学者...
    background:
      content: |
        个人经历：
        - 1960年出生于北京
        - 1985年北京大学历史学博士
        - 研究方向：秦汉政治制度
        
        学术成就：
        - 发表论文50余篇
        - 出版专著3部
        - 培养博士生20余名
      source: biography
      rag_enabled: true
      rag_top_k: 5
```

### 4.2 文件引用

对于非常长的背景，可以使用外部文件：

```yaml
background:
  file: personas/backgrounds/historian_full.txt
  source: detailed_biography
```

### 4.3 程序化配置

```python
from mul_in_one_nemo.rag import get_rag_service

rag = get_rag_service()

# 从文件加载
with open("backgrounds/historian.txt", "r") as f:
    content = f.read()

rag.add_persona_background(
    "historian",
    content,
    source="file_background",
    metadata={"version": "1.0"}
)
```

## 5. 使用场景

### 5.1 详细人物传记

适合需要丰富背景设定的角色：

```yaml
background:
  content: |
    ## 童年时期 (1960-1975)
    出生在一个书香门第...
    
    ## 求学时期 (1975-1990)
    考入北京大学...
    
    ## 职业生涯 (1990至今)
    在大学任教三十年...
    
    ## 个人生活
    爱好京剧、书法...
```

### 5.2 专业知识库

适合专家型角色：

```yaml
background:
  content: |
    ## 专业领域
    - 中医内科：擅长脾胃病、肝胆疾病
    - 针灸推拿：熟练掌握各种针法
    
    ## 常用方剂
    - 四君子汤：健脾益气
    - 六味地黄丸：滋阴补肾
    ...
```

### 5.3 世界观设定

适合虚构角色：

```yaml
background:
  content: |
    ## 世界观
    这个世界存在魔法，分为火、水、风、土四系...
    
    ## 角色背景
    我是水系魔法师，出生在海边小镇...
    
    ## 重要事件
    - 十岁那年，发现自己拥有魔法天赋
    - 十五岁进入魔法学院
    ...
```

## 6. 最佳实践

### 6.1 内容组织

- **分段落**：按主题分段，便于检索定位
- **使用标题**：添加 `##` 标题帮助组织内容
- **关键词**：确保重要概念在文本中出现

### 6.2 检索优化

- **rag_top_k 设置**：
  - 简单背景：2-3
  - 丰富背景：4-6
  - 复杂角色：6-10
  
- **source 标识**：使用有意义的 source 值，便于追踪

### 6.3 性能考虑

- 默认内存向量存储适合中小规模部署
- 大规模部署可切换到 Milvus 或 pgvector
- 考虑为频繁使用的角色预加载知识库

## 7. API 参考

### RAGService

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_or_create_knowledge_base` | `persona_handle: str` | `PersonaKnowledgeBase` | 获取或创建知识库 |
| `add_persona_background` | `persona_handle, content, source, metadata` | `List[str]` | 添加背景知识 |
| `retrieve_context` | `persona_handle, query, k` | `str` | 检索相关上下文 |
| `has_knowledge` | `persona_handle: str` | `bool` | 检查是否有知识 |
| `clear_persona_knowledge` | `persona_handle: str` | `None` | 清除特定角色知识 |
| `clear_all` | | `None` | 清除所有知识 |

### PersonaKnowledgeBase

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `add_background` | `content, source, metadata` | `List[str]` | 添加背景 |
| `retrieve` | `query, k` | `List[Document]` | 检索文档 |
| `clear` | | `None` | 清除知识库 |

## 8. 未来扩展

- [ ] 支持 Milvus 持久化向量存储
- [ ] 支持 NVIDIA NIM 嵌入 API
- [ ] 支持动态更新知识库（对话中学习）
- [ ] 支持多模态背景（图片、音频）
- [ ] 知识库版本管理
