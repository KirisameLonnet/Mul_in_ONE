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

## 4. Catchphrases 与上下文标签
- 每个口头禅须为完整短句，运行时会随机附加在系统提示尾部，帮助 LLM 维持口吻。
- 当用户输入中出现 persona `name` 或 `handle`，调度器会给该角色额外加权，鼓励点名回应。

## 5. 示例模板
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
settings:
  max_agents_per_turn: 2
  memory_window: 8
  # 多数情况下无需在 settings 下声明 API 绑定，直接在 persona 内写 `api: <api_name>` 即可。
```

## 6. 最佳实践检查表
- [ ] 角色 prompt 不少于 3 句，包含行为准则。
- [ ] 避免空泛描述，使用可执行的指令或示例语句。
- [ ] `handle` 唯一、全小写、无空格。
- [ ] `proactivity` 数值与角色调性一致。
- [ ] Catchphrases 不超过 5 条且与角色口吻匹配。
- [ ] 若需要专属 API，优先写 `api: <api_name>` 绑定集中配置；确需自定义时仅填改动项，避免泄露密钥。
- [ ] 所有文本使用 UTF-8，可混合中英但语境清晰。
