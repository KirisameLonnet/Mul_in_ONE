<template>
  <div class="session-manager">
    <!-- List View -->
    <div v-if="!currentSessionId" class="list-view">
      <div class="header">
        <h2>Sessions</h2>
        <d-button @click="handleCreateSession" variant="solid" color="primary">New Session</d-button>
      </div>
      
      <div v-if="loading" class="loading">Loading sessions...</div>
      <div v-else class="session-list">
        <div 
          v-for="session in sessions" 
          :key="session.id" 
          class="session-item"
          @click="enterSession(session.id)"
        >
          <div class="session-id">#{{ session.id }}</div>
          <div class="session-meta">
            Created: {{ new Date(session.created_at).toLocaleString() }}
          </div>
        </div>
      </div>
    </div>

    <!-- Chat View -->
    <div v-else class="chat-view">
      <div class="chat-header">
        <d-button @click="exitSession" variant="text" icon="icon-arrow-left">Back</d-button>
        <h3>Session #{{ currentSessionId }}</h3>
      </div>
      
      <div class="chat-layout">
        <div class="messages-area" ref="messagesContainer">
          <McBubble 
            v-for="msg in messages" 
            :key="msg.id"
            :content="msg.content"
            :align="msg.sender === 'user' ? 'right' : 'left'"
            :avatarConfig="{ displayName: msg.sender }"
          />
        </div>
        
        <div class="controls-area">
          <div class="persona-selector">
            <label>Target Personas:</label>
            <div class="tags">
              <d-tag 
                v-for="p in availablePersonas" 
                :key="p.id"
                :type="selectedPersonas.includes(p.handle) ? 'primary' : 'default'"
                class="persona-tag"
                @click="togglePersona(p.handle)"
              >
                @{{ p.handle }}
              </d-tag>
            </div>
          </div>
          
          <div class="input-area">
            <McInput 
              :value="newMessage" 
              @change="(val: string) => newMessage = val"
              @submit="handleSend"
              placeholder="Type a message..."
              :autoClear="true"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue';
import { 
  getSessions, 
  createSession, 
  getMessages, 
  sendMessage, 
  getPersonas,
  type Session, 
  type Message,
  type Persona,
  authState 
} from '../api';
import { createChatWebSocketUrl, type WebSocketMessage } from '../websocket';

const sessions = ref<Session[]>([]);
const messages = ref<Message[]>([]);
const availablePersonas = ref<Persona[]>([]);
const selectedPersonas = ref<string[]>([]);

const currentSessionId = ref<string | null>(null);
const loading = ref(false);
const newMessage = ref('');
const messagesContainer = ref<HTMLElement | null>(null);

// Manual WS management since the composable is a bit rigid for dynamic URLs
let activeWs: WebSocket | null = null;

function handleWsMessage(msg: WebSocketMessage) {
  const { event, data } = msg;
  
  if (event === 'agent.chunk' || event === 'agent.end') {
    const { message_id, sender, content, persisted_message_id } = data;
    
    // Find existing message by ID (temporary or persisted)
    let existingMsg = messages.value.find(m => m.id === message_id);
    
    if (existingMsg) {
      // Update existing message
      // For chunks, we append. But wait, the backend might send the *delta* or the *full* content?
      // Looking at session_service.py: 
      // normalized = event if isinstance(event, dict) else {"event": "agent.chunk", "data": {"content": str(event)}}
      // And in _handle_adapter_event:
      // if event_type == "agent.chunk": tracker["buffer"].append(content); data["content"] = content
      // So it sends the CHUNK (delta).
      
      // However, if we just append, we need to be careful about duplication if we re-fetch.
      // But here we are in streaming mode.
      
      // Wait, if I look at `session_service.py`:
      // `data["content"] = content` where content is the chunk.
      // So yes, it is the delta.
      
      // BUT, for `agent.end`, it sends `final_content`.
      
      if (event === 'agent.chunk') {
        existingMsg.content += content;
        scrollToBottom();
      } else if (event === 'agent.end') {
        // Final update to ensure consistency
        if (content) existingMsg.content = content;
        // Update ID to persisted ID if available
        if (persisted_message_id) {
          existingMsg.id = persisted_message_id;
        }
      }
    } else {
      // Create new message
      if (event === 'agent.chunk' || (event === 'agent.end' && content)) {
        messages.value.push({
          id: message_id,
          sender: sender,
          content: content || '',
          timestamp: new Date().toISOString()
        });
        scrollToBottom();
      }
    }
  }
}

const loadSessions = async () => {
  loading.value = true;
  try {
    sessions.value = await getSessions();
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const handleCreateSession = async () => {
  try {
    const id = await createSession();
    await loadSessions();
    enterSession(id);
  } catch (e) {
    alert('Failed to create session');
  }
};

const enterSession = async (id: string) => {
  currentSessionId.value = id;
  messages.value = [];
  await loadPersonas();
  await refreshMessages();
  scrollToBottom();
  
  // Setup WebSocket
  // We need to access the private 'url' property or recreate the client? 
  // The useWebSocket composable creates a client instance. We can't easily change the URL of an existing client instance 
  // if the class doesn't support it. 
  // Looking at websocket.ts, the URL is set in constructor.
  // So we should probably recreate the client or use a reactive URL if supported.
  // The current useWebSocket implementation takes options in constructor.
  // Let's manually manage the client instance here or modify useWebSocket to support url change.
  // For now, I'll just manually close and create a new connection using the exposed client if possible, 
  // but the `useWebSocket` returns a single client instance bound to the options.
  
  // Workaround: We'll just use the raw WebSocketClient class or create a new useWebSocket scope?
  // Actually, let's just modify the client.url directly if it was public, but it's private.
  // Let's just re-instantiate the logic here without the composable for full control, 
  // OR (better) just use the client.close() and create a new one.
  
  // Let's use a ref for the client to allow replacement
  if (activeWs) {
    activeWs.close();
  }
  
  // Re-initialize connection with new URL
  // Since useWebSocket returns a static client object, we can't "change" its URL.
  // We will implement a simple connect function here that creates a new WebSocket.
  initWebSocket(id);
};

const initWebSocket = (sessionId: string) => {
  if (activeWs) {
    activeWs.close();
  }
  
  const url = createChatWebSocketUrl(sessionId);
  console.log('Connecting WS to', url);
  
  activeWs = new WebSocket(url);
  
  activeWs.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWsMessage(msg);
    } catch (e) {
      console.error('WS parse error', e);
    }
  };
  
  activeWs.onclose = () => {
    console.log('WS Closed');
  };
};

const exitSession = () => {
  if (activeWs) {
    activeWs.close();
    activeWs = null;
  }
  currentSessionId.value = null;
  loadSessions();
};

const loadPersonas = async () => {
  try {
    availablePersonas.value = await getPersonas(authState.username);
  } catch (e) {
    console.error(e);
  }
};

const togglePersona = (handle: string) => {
  if (selectedPersonas.value.includes(handle)) {
    selectedPersonas.value = selectedPersonas.value.filter(h => h !== handle);
  } else {
    selectedPersonas.value.push(handle);
  }
};

const refreshMessages = async () => {
  if (!currentSessionId.value) return;
  try {
    const msgs = await getMessages(currentSessionId.value);
    const shouldScroll = msgs.length > messages.value.length;
    messages.value = msgs;
    if (shouldScroll) scrollToBottom();
  } catch (e) {
    console.error(e);
  }
};

const handleSend = async (content: string) => {
  if (!content.trim() || !currentSessionId.value) return;
  
  const targets = [...selectedPersonas.value];
  
  try {
    // Optimistic update
    messages.value.push({
      id: 'temp-' + Date.now(),
      sender: 'user',
      content: content,
      timestamp: new Date().toISOString()
    });
    scrollToBottom();

    await sendMessage(currentSessionId.value, content, targets);
    // We don't need to refreshMessages immediately if WS is working, 
    // but it's safe to do so to get the server-side ID of the user message.
    // await refreshMessages(); 
  } catch (e) {
    alert('Failed to send message');
    console.error(e);
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

onMounted(loadSessions);
onUnmounted(() => {
  if (activeWs) activeWs.close();
});
</script>

<style scoped>
.session-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header, .chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
  background: white;
}

.session-list {
  padding: 1rem;
  overflow-y: auto;
}

.session-item {
  padding: 1rem;
  border: 1px solid #eee;
  border-radius: 8px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  background: white;
  transition: background 0.2s;
}

.session-item:hover {
  background: #f5f5f5;
  border-color: #4a90e2;
}

.session-id {
  font-weight: bold;
  color: #333;
}

.session-meta {
  font-size: 0.85em;
  color: #888;
}

.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.controls-area {
  padding: 1rem;
  background: white;
  border-top: 1px solid #eee;
}

.persona-selector {
  margin-bottom: 0.5rem;
}

.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}

.persona-tag {
  cursor: pointer;
}

.input-area {
  margin-top: 1rem;
}
</style>
