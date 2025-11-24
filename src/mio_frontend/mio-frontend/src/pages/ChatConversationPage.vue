<template>
  <McLayout class="chat-page">
    <!-- 顶部 Header -->
    <McHeader :title="`Chat Session`" :logoImg="logoUrl">
      <template #operationArea>
        <div class="header-operations">
          <div class="agent-selector">
            <i class="icon-at"></i>
            <d-select
              v-model="selectedPersonas"
              :options="personaOptions"
              multiple
              placeholder="Select Target Agents"
              size="sm"
              class="agent-select"
            />
          </div>
          <div class="header-actions">
            <i class="icon-helping" title="Help"></i>
            <i class="icon-close" @click="goBack" title="Close"></i>
          </div>
        </div>
      </template>
    </McHeader>

    <!-- 消息内容区域 -->
    <McLayoutContent class="chat-content" ref="contentRef">
      <div v-if="loading" class="loading-state">
        <d-loading></d-loading>
        <p class="loading-text">Loading conversation...</p>
      </div>
      
      <div v-else-if="messages.length === 0" class="empty-state">
        <McIntroduction
          :logoImg="logoUrl"
          :title="'Multi-Agent Chat'"
          :subTitle="'Hi, Welcome to Mul-in-One'"
          :description="introDescription"
        />
        <McPrompt
          :list="quickPrompts"
          :direction="'horizontal'"
          class="intro-prompts"
          @itemClick="handlePromptClick"
        />
      </div>

      <template v-else>
        <template v-for="(msg, idx) in messages" :key="msg.id || idx">
          <McBubble
            v-if="msg.sender === 'user'"
            :content="msg.content"
            :align="'right'"
            :avatarConfig="{ 
              imgSrc: userAvatar,
              name: 'You' 
            }"
            class="message-bubble user-bubble"
          />
          <McBubble
            v-else
            :content="msg.content"
            :align="'left'"
            :avatarConfig="{ 
              imgSrc: agentAvatar,
              name: msg.sender || 'Agent' 
            }"
            :loading="msg.loading"
            class="message-bubble agent-bubble"
          />
        </template>
      </template>
    </McLayoutContent>

    <!-- 快捷提示词（当有消息时显示） -->
    <div v-if="messages.length > 0" class="shortcut-prompts">
      <McPrompt
        :list="simplePrompts"
        :direction="'horizontal'"
        @itemClick="handlePromptClick"
      />
    </div>

    <!-- 底部输入区 -->
    <McLayoutSender>
      <McInput
        :value="inputValue"
        :maxLength="2000"
        :placeholder="inputPlaceholder"
        @change="handleInputChange"
        @submit="handleSubmit"
        :disabled="sending"
      >
        <template #extra>
          <div class="input-footer">
            <div class="input-footer-left">
              <span class="input-action">
                <i class="icon-at"></i>
                Agents
              </span>
              <span class="input-action">
                <i class="icon-standard"></i>
                Templates
              </span>
              <span class="input-action">
                <i class="icon-add"></i>
                Attachment
              </span>
              <span class="input-divider"></span>
              <span class="input-counter">{{ inputValue.length }}/2000</span>
            </div>
            <div class="input-footer-right">
              <d-button
                variant="text"
                size="sm"
                :disabled="!inputValue.trim()"
                @click="clearInput"
              >
                <i class="icon-op-clearup"></i>
                <span class="button-text">Clear</span>
              </d-button>
            </div>
          </div>
        </template>
      </McInput>
    </McLayoutSender>
  </McLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMessages, sendMessage, getPersonas, type Message, type Persona, authState } from '../api'
import { useWebSocket, createChatWebSocketUrl, type WebSocketMessage } from '../websocket'

const route = useRoute()
const router = useRouter()
const sessionId = route.params.id as string

// Assets
const logoUrl = 'https://matechat.gitcode.com/logo.svg'
const userAvatar = 'https://matechat.gitcode.com/png/demo/userAvatar.svg'
const agentAvatar = 'https://matechat.gitcode.com/logo.svg'

// Introduction content
const introDescription = [
  'Mul-in-One enables multi-agent collaboration for complex tasks.',
  'You can select specific agents to handle your requests, or let all agents work together.',
  'Your feedback helps improve the system performance.',
]

// Quick prompts
const quickPrompts = [
  {
    value: 'help',
    label: 'What can you help me with?',
    iconConfig: { name: 'icon-star', color: '#ffd700' },
    desc: 'Learn about available features and capabilities'
  },
  {
    value: 'agents',
    label: 'Show available agents',
    iconConfig: { name: 'icon-user-group', color: '#5e7ce0' },
    desc: 'View all configured agents and their roles'
  },
  {
    value: 'example',
    label: 'Give me an example',
    iconConfig: { name: 'icon-info-o', color: '#3ac295' },
    desc: 'See example interactions and use cases'
  },
]

const simplePrompts = [
  {
    value: 'continue',
    label: 'Continue',
    iconConfig: { name: 'icon-play', color: '#5e7ce0' },
  },
  {
    value: 'clarify',
    label: 'Please clarify',
    iconConfig: { name: 'icon-help', color: '#ffa500' },
  },
]

interface MessageWithLoading extends Message {
  loading?: boolean
}

const messages = ref<MessageWithLoading[]>([])
const availablePersonas = ref<Persona[]>([])
const selectedPersonas = ref<string[]>([])
const loading = ref(false)
const sending = ref(false)
const inputValue = ref('')
const contentRef = ref<HTMLElement | null>(null)

// 处理代理开始回复
const handleAgentStart = (data: any) => {
  const agentMessage: MessageWithLoading = {
    id: data.message_id || `agent-${Date.now()}`,
    sender: data.sender || 'agent',
    content: '',
    timestamp: data.timestamp || new Date().toISOString(),
    loading: true
  }
  messages.value.push(agentMessage)
  nextTick(() => scrollToBottom())
}

// 处理流式内容块
const handleAgentChunk = (data: any) => {
  // 查找最后一条 loading 状态的代理消息
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const msg = messages.value[i]
    if (msg && msg.loading && msg.sender !== 'user') {
      // 追加内容
      msg.content += (data.content || data.text || data)
      // 滚动到底部（流畅追加效果）
      nextTick(() => scrollToBottom())
      break
    }
  }
}

// 处理代理回复完成
const handleAgentEnd = (data: any) => {
  // 找到对应的消息并取消 loading 状态
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const msg = messages.value[i]
    if (msg && msg.loading && (msg.id === data.message_id || msg.sender !== 'user')) {
      msg.loading = false
      // 如果有完整内容，使用完整内容
      if (data.content) {
        msg.content = data.content
      }
      break
    }
  }
}

// 处理新消息（完整消息）
const handleNewMessage = (data: any) => {
  const newMessage: MessageWithLoading = {
    id: data.id,
    sender: data.sender,
    content: data.content,
    timestamp: data.timestamp
  }
  messages.value.push(newMessage)
  nextTick(() => scrollToBottom())
}

// 处理 WebSocket 消息
const handleWebSocketMessage = (message: WebSocketMessage) => {
  console.log('Processing WebSocket message:', message)
  
  switch (message.event) {
    case 'agent.chunk':
      // 流式追加消息内容
      handleAgentChunk(message.data)
      break
    
    case 'agent.start':
      // 代理开始回复
      handleAgentStart(message.data)
      break
    
    case 'agent.end':
      // 代理回复完成
      handleAgentEnd(message.data)
      break
    
    case 'message.new':
      // 新消息（完整消息）
      handleNewMessage(message.data)
      break
    
    default:
      console.log('Unknown message event:', message.event)
  }
}

// WebSocket 连接
const wsUrl = createChatWebSocketUrl(sessionId)
useWebSocket({
  url: wsUrl,
  reconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  onMessage: handleWebSocketMessage,
  onOpen: () => {
    console.log('WebSocket connected to session:', sessionId)
  },
  onClose: () => {
    console.log('WebSocket disconnected from session:', sessionId)
  },
  onError: (error) => {
    console.error('WebSocket error:', error)
  }
})

const personaOptions = computed(() => {
  return availablePersonas.value.map(p => ({
    label: `${p.name} (@${p.handle})`,
    value: p.handle
  }))
})

const inputPlaceholder = computed(() => {
  if (selectedPersonas.value.length > 0) {
    return `Message to ${selectedPersonas.value.join(', ')}...`
  }
  return 'Type your message here...'
})

const loadData = async () => {
  loading.value = true
  try {
    const [msgs, personas] = await Promise.all([
      getMessages(sessionId),
      getPersonas(authState.tenantId)
    ])
    messages.value = msgs
    availablePersonas.value = personas
    await nextTick()
    scrollToBottom()
  } catch (e) {
    console.error('Failed to load chat data:', e)
  } finally {
    loading.value = false
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (contentRef.value) {
      const container = (contentRef.value as any).$el || contentRef.value
      if (container && container.scrollTo) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        })
      }
    }
  })
}

const handleInputChange = (value: string) => {
  inputValue.value = value
}

const handlePromptClick = (item: any) => {
  handleSubmit(item.label)
}

const handleSubmit = async (content: string) => {
  const messageContent = typeof content === 'string' ? content : inputValue.value
  if (!messageContent.trim()) return
  
  sending.value = true
  const targets = selectedPersonas.value

  // Optimistic UI update
  messages.value.push({
    id: 'temp-' + Date.now(),
    sender: 'user',
    content: messageContent,
    timestamp: new Date().toISOString()
  })
  
  inputValue.value = ''
  await nextTick()
  scrollToBottom()

  try {
    await sendMessage(sessionId, messageContent, targets)
    // WebSocket 会实时推送代理的响应，无需手动刷新
  } catch (e) {
    console.error('Failed to send message:', e)
    // Remove optimistic message on error
    messages.value = messages.value.filter(m => !m.id.toString().startsWith('temp-'))
  } finally {
    sending.value = false
  }
}

const clearInput = () => {
  inputValue.value = ''
}

const goBack = () => {
  router.push('/sessions')
}

onMounted(() => {
  loadData()
  // WebSocket 会自动在 useWebSocket 中连接，无需轮询
})
</script>

<style scoped>
/* 主容器 */
.chat-page {
  width: 100%;
  max-width: 1200px;
  height: calc(100vh - 40px);
  margin: 20px auto;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e5e6eb;
  border-radius: 16px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Header 样式 */
.header-operations {
  display: flex;
  align-items: center;
  gap: 16px;
}

.agent-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.agent-selector i {
  font-size: 18px;
  color: #5e7ce0;
}

.agent-select {
  min-width: 200px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-actions i {
  font-size: 20px;
  color: #575d6c;
  cursor: pointer;
  transition: color 0.3s;
}

.header-actions i:hover {
  color: #5e7ce0;
}

/* 内容区域 */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding: 16px;
  background: #fafbfc;
  border-radius: 12px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.loading-text {
  font-size: 14px;
  color: #8f959e;
  margin: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  height: 100%;
}

.intro-prompts {
  width: 100%;
  max-width: 800px;
}

/* 消息气泡 */
.message-bubble {
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-bubble :deep(.mc-bubble-content) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 4px 12px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.agent-bubble :deep(.mc-bubble-content) {
  background: white;
  color: #252b3a;
  border-radius: 12px 12px 12px 4px;
  padding: 12px 16px;
  border: 1px solid #e5e6eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* 快捷提示词 */
.shortcut-prompts {
  padding: 8px 16px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e5e6eb;
}

/* 输入区域底部 */
.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 12px;
  background: #fafbfc;
  border-top: 1px solid #e5e6eb;
}

.input-footer-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.input-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #575d6c;
  cursor: pointer;
  transition: color 0.3s;
}

.input-action:hover {
  color: #5e7ce0;
}

.input-action i {
  font-size: 16px;
}

.input-divider {
  width: 1px;
  height: 16px;
  background-color: #d7d8da;
}

.input-counter {
  font-size: 14px;
  color: #8f959e;
}

.input-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.button-text {
  margin-left: 4px;
  font-size: 14px;
}

/* 滚动条美化 */
.chat-content::-webkit-scrollbar {
  width: 6px;
}

.chat-content::-webkit-scrollbar-track {
  background: transparent;
}

.chat-content::-webkit-scrollbar-thumb {
  background: #d7d8da;
  border-radius: 3px;
}

.chat-content::-webkit-scrollbar-thumb:hover {
  background: #bbbfc4;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-page {
    margin: 0;
    border-radius: 0;
    height: 100vh;
  }

  .agent-selector {
    flex-direction: column;
    align-items: flex-start;
  }

  .input-footer-left {
    flex-wrap: wrap;
  }

  .input-action {
    font-size: 12px;
  }
}

/* MateChat 组件样式覆盖 */
:deep(.mc-layout) {
  border: none;
  box-shadow: none;
}

:deep(.mc-header) {
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

:deep(.mc-header-title) {
  font-size: 20px;
  font-weight: 600;
  color: white;
}

:deep(.mc-bubble) {
  max-width: 75%;
}

:deep(.mc-bubble-content) {
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
}

:deep(.mc-input-textarea) {
  min-height: 60px;
  font-size: 15px;
  border-radius: 8px;
}

:deep(.mc-introduction) {
  text-align: center;
}

:deep(.mc-introduction-title) {
  font-size: 28px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

:deep(.mc-prompt-item) {
  transition: all 0.3s;
  border-radius: 8px;
  padding: 12px 16px;
}

:deep(.mc-prompt-item:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}
</style>
