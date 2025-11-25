# Persona Prompt & YAML Spec

为角色扮演场景建立统一规范，确保 persona 配置在 CLI、调度器与 NeMo Workflow 中表现一致。

## 1. 数据结构
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | ✅ | 角色在界面显示的中文/英文名，亦作为 scheduler 标签。 |
| `handle` | string | ✅ | 唯一 ID（建议全小写英文），用于命令行 @ 指定与 Workflow function 名称。 |
| `prompt` | multiline string | ✅ | Persona 主提示词：角色背景、目标、行为准则。遵循下文写作规范。 |
| `tone` | string | ⚪️ | 描述语气，供系统提示/日志使用（例如 `gentle`、`serious`）。 |
| `proactivity` | float 0~1 | ⚪️ | 调度器主动度，越高越容易被选中发言。默认 `0.5`。 |
| `catchphrases` | list[string] | ⚪️ | 常用口头禅，供系统提示追加上下文。 |
| `api` | object | ⚪️ | 可选的专属 API 配置（见下文），未填写则回落到全局 `Settings`。 |
| `background` | string/object | ⚪️ | 角色背景知识，支持 RAG 检索增强（见下文）。 |
| `settings.max_agents_per_turn` | int | ⚪️ | 单回合最多 persona 数，覆盖全局设置。 |
| `settings.memory_window` | int | ⚪️ | LLM 每次可见的历史消息数，覆盖全局设置。 |

## 2. Persona Prompt 写作规范
1. **角色定位明确**：首段交代身份、背景、价值观，说明面向用户/其他 AI 的态度。
2. **行为准则列举**：使用短句描述做事方式，例如“先共情再给建议”“严禁泄露现实世界身份”。
3. **对话风格要点**：包含语气、节奏、是否使用 emoji、是否引用网络梗等。
4. **群聊协作提示**：说明与其他 persona 的互动策略（让谁先说、遇到冲突如何回应）。
5. **边界 & 安全**：指出禁止的输出（攻击性内容、敏感信息等）；如需避雷词请明确列出。
6. **语言要求**：指定默认语言或混合方式，避免模型自动切换。

建议模板：
```
你是 <身份>，主要目标是 <目标>。
- 风格：<语气/节奏/emoji 约束>
- 与他人互动：<如何协作>
- 安全：<禁止点>
- 任务偏好：<擅长或避免的主题>
``` 

## 3. Tone / Proactivity 设置
- `tone` 字段不直接影响模型，但 CLI 会在系统提示中附带“语气倾向”，帮助 LLM 收敛输出。
- `proactivity` 建议根据 persona 角色定位设置：
  - 0.8 以上：活跃气氛、打断能力强的角色。
  - 0.4~0.7：常规角色，平衡对话。
  - 0.2 以下：专家型、只在必要时发言。

## 4. API 配置与绑定
- Persona 可以在自身 YAML 中写入 `api` 字段：
  - 若值为字符串，表示引用集中式 API 配置中的某个 `name`（推荐）。
  - 若值为对象，则可覆盖 `model`/`base_url`/`api_key`/`temperature` 等字段。
- 通过 `MUL_IN_ONE_API_CONFIG` 或 `--api-config` 指定集中式 YAML：
  - `apis[]`：记录 `name`、`base_url|provider_url`、`model`、`api_key`、`temperature`。
  - `default_api`：未绑定 persona 时使用的默认配置。
  - （可选）`persona_bindings`：`persona`（handle 或 name）→ `api` name 的映射；若已在 persona YAML 中写明 `api: some_api_name` 通常无需此项。
- CLI 启动时会将绑定写入 persona：若 persona YAML 只覆盖部分字段，则与绑定配置合并，其余字段回落到默认 API。

### API 配置回落逻辑
`api` 支持四个键：

| 键 | 说明 | 默认来源 |
| --- | --- | --- |
| `model` | NIM 模型名 | `Settings.nim_model` |
| `base_url` | NIM 访问地址 | `Settings.nim_base_url` |
| `api_key` | 私有密钥 | `Settings.nim_api_key` / `NVIDIA_API_KEY` |
| `temperature` | 采样温度 | `Settings.temperature` |

当 persona 提供 `api` 字段时，会为其注册独立的 LLM 客户端；未提供的字段逐项继承全局配置。未写 `api` 则与其它 persona 共用默认 LLM。

## 5. Background（RAG 背景知识）

`background` 字段用于配置角色的长期背景知识，通过 RAG（检索增强生成）技术在对话时动态检索相关内容。这对于拥有丰富经历或专业知识的角色特别有用。

### 使用场景
- 角色有详细的人生经历/背景故事
- 角色具有大量专业知识或世界观设定
- 背景内容太长无法全部放入每次提示词中

### 配置方式

**简单字符串格式**（直接写入背景文本）：
```yaml
background: |
  我出生在上海，从小对文学有浓厚兴趣。
  大学时期主修中国古典文学，毕业后成为一名作家。
  我出版过三本小说，获得过某某文学奖。
```

**完整配置格式**：
```yaml
background:
  content: |
    我的背景故事...
  file: personas/backgrounds/historian.txt  # 可选，从文件加载
  source: life_story  # 来源标识，用于检索时区分
  rag_enabled: true   # 是否启用 RAG（默认 true）
  rag_top_k: 3        # 检索返回的相关片段数量（默认 3）
```

### Background 配置字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `content` | string | ⚪️ | 内联的背景文本内容 |
| `file` | string | ⚪️ | 背景文本文件路径（相对或绝对路径） |
| `source` | string | ⚪️ | 来源标识，默认 `background` |
| `rag_enabled` | bool | ⚪️ | 是否启用 RAG 检索，默认 `true` |
| `rag_top_k` | int | ⚪️ | 检索返回的相关片段数量，默认 `3` |

### 工作原理
1. 启动时，背景文本会被切分成小块并建立向量索引
2. 对话时，系统根据当前对话上下文检索最相关的背景片段
3. 检索到的内容会被注入到系统提示词中，帮助角色"回忆"相关经历
4. 角色可以自然地在对话中引用这些背景知识

### 示例

```yaml
personas:
  - name: 历史学家老王
    handle: historian
    tone: scholarly
    proactivity: 0.6
    prompt: |
      你是一位资深历史学家，专攻中国古代史。
      说话风格学术但不失幽默，喜欢引经据典。
    background:
      content: |
        我1960年出生在北京，父亲是北大历史系教授。
        1978年考入北京大学历史系，师从著名历史学家某某先生。
        1985年获得博士学位，研究方向是秦汉政治制度史。
        
        学术经历：
        - 1985-1990：北大历史系讲师
        - 1990-2000：副教授，期间在哈佛大学访学两年
        - 2000至今：教授，博士生导师
        
        代表作品：
        - 《秦汉官僚制度研究》（1992）
        - 《中国古代政治文化》（2005）
        - 《历史的温度》（2018，科普读物）
        
        个人爱好：
        - 京剧、书法、品茶
        - 喜欢在课堂上讲历史故事
      source: biography
      rag_top_k: 5
```

## 6. Catchphrases 与上下文标签
- 每个口头禅须为完整短句，运行时会随机附加在系统提示尾部，帮助 LLM 维持口吻。
- 当用户输入中出现 persona `name` 或 `handle`，调度器会给该角色额外加权，鼓励点名回应。

## 7. 示例模板
```yaml
personas:
  - name: 未来系作曲家
    handle: composer
    tone: dreamy
    proactivity: 0.65
    api: composer_special
    prompt: |
      你是未来系电子音乐作曲家，喜欢把科技与诗意结合。
      - 风格：常用比喻，引用合成器术语，偶尔附上 🎹🎧 emoji。
      - 互动：尊重其他角色的观点，用音乐隐喻衔接话题。
      - 安全：不提供医疗/法律建议，不过度夸大现实效果。
    catchphrases:
      - "节奏要让心跳对齐"
      - "这段和弦还能再铺陈"
    background: |
      我在维也纳音乐学院学习了五年电子音乐制作。
      曾与多位知名艺术家合作，作品被收录在多张专辑中。
      我最喜欢的合成器是 Moog 和 Prophet。
settings:
  max_agents_per_turn: 2
  memory_window: 8
  # 多数情况下无需在 settings 下声明 API 绑定，直接在 persona 内写 `api: <api_name>` 即可。
```

## 8. 最佳实践检查表
- [ ] 角色 prompt 不少于 3 句，包含行为准则。
- [ ] 避免空泛描述，使用可执行的指令或示例语句。
- [ ] `handle` 唯一、全小写、无空格。
- [ ] `proactivity` 数值与角色调性一致。
- [ ] Catchphrases 不超过 5 条且与角色口吻匹配。
- [ ] 若需要专属 API，优先写 `api: <api_name>` 绑定集中配置；确需自定义时仅填改动项，避免泄露密钥。
- [ ] 所有文本使用 UTF-8，可混合中英但语境清晰。
- [ ] 对于背景丰富的角色，使用 `background` 字段配置 RAG，避免 prompt 过长。
- [ ] Background 内容应结构化，分段落描述不同方面（经历、专长、爱好等）。
