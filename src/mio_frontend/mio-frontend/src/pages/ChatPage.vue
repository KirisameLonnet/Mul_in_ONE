<template>
  <q-page class="flex column" style="height: calc(100vh - 50px);">
    <!-- Chat Area -->
    <div class="col scroll q-pa-md" ref="chatContainer">
      <div v-if="loading" class="flex flex-center full-height">
        <q-spinner size="3em" color="primary" />
      </div>
      <div v-else>
        <McBubble 
          v-for="msg in messages" 
          :key="msg.id"
          :content="msg.content"
          :align="msg.sender === 'user' ? 'right' : 'left'"
          :avatarConfig="{ displayName: msg.sender }"
          class="q-mb-md"
        />
      </div>
    </div>

    <!-- Input Area -->
    <div class="q-pa-md bg-grey-2 border-top">
      <div class="row items-center q-mb-sm">
        <div class="text-caption q-mr-sm">Target Agents:</div>
        <q-select
          v-model="selectedPersonas"
          :options="availablePersonas"
          option-value="handle"
          option-label="handle"
          multiple
          dense
          outlined
          options-dense
          use-chips
          stack-label
          label="Select Agents"
          style="min-width: 200px; flex-grow: 1;"
          emit-value
          map-options
        />
      </div>
      <q-input
        v-model="newMessage"
        outlined
        dense
        placeholder="Type a message..."
        @keyup.enter="sendMessageHandler"
        :loading="sending"
      >
        <template v-slot:after>
          <q-btn round dense flat icon="send" color="primary" @click="sendMessageHandler" :disable="!newMessage.trim() || sending" />
        </template>
      </q-input>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { getMessages, sendMessage, getPersonas, type Message, type Persona, authState } from '../api'

const route = useRoute()
const $q = useQuasar()
const sessionId = route.params.id as string

const messages = ref<Message[]>([])
const availablePersonas = ref<Persona[]>([])
const selectedPersonas = ref<string[]>([])
const newMessage = ref('')
const loading = ref(false)
const sending = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
let pollInterval: any = null

const loadData = async () => {
  loading.value = true
  try {
    const [msgs, personas] = await Promise.all([
      getMessages(sessionId),
      getPersonas(authState.tenantId)
    ])
    messages.value = msgs
    availablePersonas.value = personas
    scrollToBottom()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to load chat data' })
  } finally {
    loading.value = false
  }
}

const refreshMessages = async () => {
  try {
    const msgs = await getMessages(sessionId)
    if (msgs.length !== messages.value.length) {
      messages.value = msgs
      scrollToBottom()
    }
  } catch (e) {
    console.error('Polling failed', e)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

const sendMessageHandler = async () => {
  if (!newMessage.value.trim()) return
  
  sending.value = true
  const content = newMessage.value
  const targets = selectedPersonas.value
  
  // Optimistic update
  messages.value.push({
    id: 'temp-' + Date.now(),
    sender: 'user',
    content: content,
    timestamp: new Date().toISOString()
  })
  newMessage.value = ''
  scrollToBottom()

  try {
    await sendMessage(sessionId, content, targets)
    await refreshMessages()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Failed to send message' })
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  loadData()
  pollInterval = setInterval(refreshMessages, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.border-top {
  border-top: 1px solid #e0e0e0;
}
</style>
