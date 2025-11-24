import { ref, onUnmounted } from 'vue'

export interface WebSocketMessage {
  event: string
  data: any
}

export interface WebSocketOptions {
  url: string
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (message: WebSocketMessage) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
}

/**
 * WebSocket 客户端封装
 * 提供自动重连、消息处理等功能
 */
export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnect: boolean
  private reconnectInterval: number
  private maxReconnectAttempts: number
  private reconnectAttempts: number = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private isManualClose: boolean = false
  
  public onMessage?: (message: WebSocketMessage) => void
  public onOpen?: () => void
  public onClose?: () => void
  public onError?: (error: Event) => void
  
  public isConnected = ref(false)
  public isConnecting = ref(false)

  constructor(options: WebSocketOptions) {
    this.url = options.url
    this.reconnect = options.reconnect ?? true
    this.reconnectInterval = options.reconnectInterval ?? 3000
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10
    this.onMessage = options.onMessage
    this.onOpen = options.onOpen
    this.onClose = options.onClose
    this.onError = options.onError
  }

  /**
   * 连接 WebSocket
   */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      console.log('[WebSocket] Already connected or connecting')
      return
    }

    this.isManualClose = false
    this.isConnecting.value = true

    try {
      console.log('[WebSocket] Connecting to:', this.url)
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('[WebSocket] Connected')
        this.isConnected.value = true
        this.isConnecting.value = false
        this.reconnectAttempts = 0
        this.onOpen?.()
      }

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          console.log('[WebSocket] Received:', message)
          this.onMessage?.(message)
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error, event.data)
        }
      }

      this.ws.onerror = (error: Event) => {
        console.error('[WebSocket] Error:', error)
        this.isConnecting.value = false
        this.onError?.(error)
      }

      this.ws.onclose = (event: CloseEvent) => {
        console.log('[WebSocket] Closed:', event.code, event.reason)
        this.isConnected.value = false
        this.isConnecting.value = false
        this.onClose?.()

        // 自动重连（如果不是手动关闭）
        if (!this.isManualClose && this.reconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`[WebSocket] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
          this.reconnectTimer = setTimeout(() => {
            this.connect()
          }, this.reconnectInterval)
        } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          console.error('[WebSocket] Max reconnection attempts reached')
        }
      }
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error)
      this.isConnecting.value = false
    }
  }

  /**
   * 发送消息
   */
  send(message: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error('[WebSocket] Cannot send message: not connected')
      return false
    }

    try {
      const data = typeof message === 'string' ? message : JSON.stringify(message)
      this.ws.send(data)
      console.log('[WebSocket] Sent:', data)
      return true
    } catch (error) {
      console.error('[WebSocket] Failed to send message:', error)
      return false
    }
  }

  /**
   * 关闭连接
   */
  close(code: number = 1000, reason: string = 'Client closed') {
    this.isManualClose = true
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close(code, reason)
      this.ws = null
    }

    this.isConnected.value = false
    this.isConnecting.value = false
    this.reconnectAttempts = 0
  }
}

/**
 * Vue Composable for WebSocket
 * 简化在 Vue 组件中使用 WebSocket 的方式
 */
export function useWebSocket(options: WebSocketOptions) {
  const client = new WebSocketClient(options)
  
  // 组件卸载时自动关闭连接
  onUnmounted(() => {
    client.close()
  })

  return {
    client,
    isConnected: client.isConnected,
    isConnecting: client.isConnecting,
    connect: () => client.connect(),
    send: (message: any) => client.send(message),
    close: (code?: number, reason?: string) => client.close(code, reason),
  }
}

/**
 * 为聊天会话创建 WebSocket URL
 */
export function createChatWebSocketUrl(sessionId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/api/ws/sessions/${sessionId}`
}
