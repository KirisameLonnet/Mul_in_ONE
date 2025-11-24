import { ref, onUnmounted } from 'vue';
import { createSession, getMessages, sendMessage, type Message } from '../api';

export function useChat() {
  const tenantId = ref('default_tenant');
  const userId = ref('user_' + Math.floor(Math.random() * 10000));
  const sessionId = ref('');
  const loading = ref(true);
  const messages = ref<Message[]>([]);
  const streamingContent = ref('');
  let socket: WebSocket | null = null;

  const initSession = async () => {
    loading.value = true;
    try {
      const sid = await createSession(tenantId.value, userId.value);
      sessionId.value = sid;
      await loadHistory(sid);
      connectWebSocket(sid);
    } catch (e) {
      console.error('Session creation failed', e);
    } finally {
      loading.value = false;
    }
  };

  const loadHistory = async (sid: string) => {
    try {
      const history = await getMessages(sid);
      messages.value = history.slice().reverse();
    } catch (e) {
      console.error('Failed to load history', e);
    }
  };

  const connectWebSocket = (sid: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/sessions/${sid}`;

    console.log('Connecting to WS:', wsUrl);
    socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'agent.chunk') {
          streamingContent.value += data.data;
        }
      } catch (e) {
        console.error('WS Error', e);
      }
    };

    socket.onclose = (e) => {
      console.log('WebSocket closed', e);
      if (streamingContent.value) {
        commitStreamingMessage();
      }
    };

    socket.onerror = (e) => {
      console.error('WebSocket error', e);
    };
  };

  const commitStreamingMessage = () => {
    if (!streamingContent.value) return;
    messages.value.push({
      id: 'agent-' + Date.now(),
      sender: 'agent',
      content: streamingContent.value,
      timestamp: new Date().toISOString()
    });
    streamingContent.value = '';
  };

  const sendUserMessage = async (content: string) => {
    if (!content.trim()) return;

    if (streamingContent.value) {
      commitStreamingMessage();
    }

    // Optimistic update
    messages.value.push({
      id: 'temp-' + Date.now(),
      sender: 'user',
      content: content,
      timestamp: new Date().toISOString()
    });

    try {
      await sendMessage(sessionId.value, content);
    } catch (e) {
      console.error('Send failed', e);
      // Handle error (maybe remove the optimistic message or show error)
    }
  };

  onUnmounted(() => {
    if (socket) {
      socket.close();
    }
  });

  return {
    sessionId,
    loading,
    messages,
    streamingContent,
    initSession,
    sendUserMessage,
    tenantId // Export tenantId
  };
}
