import { ref, nextTick } from 'vue'
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'
import {
  createSessionApi,
  listSessionsApi,
  loadSessionApi,
  deleteSessionApi,
  type SessionInfo,
  type SessionMessage,
} from '../api/session'

// ========== 类型 ==========
export interface AssistantMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  action?: ToolCallAction
}

export interface ToolCallAction {
  type: string
  label: string
  payload?: unknown
}

export interface ToolAckPayload {
  [key: string]: unknown
}

export type { SessionInfo }

// ========== 工具函数 ==========
function formatTime(date: Date): string {
  const h = date.getHours().toString().padStart(2, '0')
  const m = date.getMinutes().toString().padStart(2, '0')
  return `${h}:${m}`
}

function getWsUrl() {
  const configured = import.meta.env.VITE_AI_WS_URL as string | undefined
  if (configured) return configured
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/chat`
}

const WS_URL = getWsUrl()
const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_BASE_DELAY = 1000
const AGENT_RESPONSE_TIMEOUT = 10 * 60 * 1000

export const useAssistantStore = defineStore('assistant', () => {
  // ========== 导航权限 ==========
  const NAV_PERMISSION_KEY = 'ai_nav_permission'
  function loadNavPermission(): boolean {
    try { return localStorage.getItem(NAV_PERMISSION_KEY) === '1' } catch { return false }
  }

  // ========== 状态 ==========
  const messages = ref<AssistantMessage[]>([])
  const sending = ref(false)
  const widgetOpen = ref(false)
  const widgetMinimized = ref(false)
  const panelExpanded = ref(false)
  const pendingAction = ref<ToolCallAction | null>(null)
  const pendingActionAcked = ref(false)
  const pendingActionExecuting = ref(false)
  const navigationPermissionGranted = ref(loadNavPermission())
  const sessionId = ref<string | null>(null)
  const sessions = ref<SessionInfo[]>([])
  const activeUserId = ref<number | null>(null)
  const initialized = ref(false)

  // ========== WebSocket（仅用于聊天流式传输） ==========
  let ws: WebSocket | null = null
  let wsReconnectAttempts = 0
  let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let wsManualClose = false

  // 聊天流 handler
  type MessageHandler = {
    onToken: (text: string) => void
    onDone: () => void
    onError: (err: string) => void
    onToolCall: (action: ToolCallAction) => void
  }
  let handler: MessageHandler | null = null

  function connectWs(): Promise<WebSocket> {
    return new Promise((resolve, reject) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        resolve(ws)
        return
      }

      if (ws && ws.readyState === WebSocket.CONNECTING) {
        const check = setInterval(() => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            clearInterval(check)
            resolve(ws)
          }
        }, 100)
        return
      }

      if (ws) {
        ws.close()
        ws = null
      }

      wsManualClose = false
      const socket = new WebSocket(WS_URL)
      ws = socket

      socket.onopen = () => {
        wsReconnectAttempts = 0
        resolve(socket)
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string)
          const t = data.type as string

          switch (t) {
            case 'session_created':
              sessionId.value = data.session_id as string
              break
            case 'token':
              if (!handler) return
              handler.onToken(data.content as string)
              break
            case 'done':
              if (!handler) return
              handler.onDone()
              handler = null
              break
            case 'error':
              if (!handler) return
              handler.onError(data.message || '服务器错误')
              handler = null
              break
            case 'tool_call':
              if (!handler) return
              handler.onToolCall(data.action as ToolCallAction)
              break
          }
        } catch {
          // 非 JSON 消息忽略
        }
      }

      socket.onclose = () => {
        if (handler) {
          handler.onError('连接已断开')
          handler = null
        }
        if (!wsManualClose && wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_BASE_DELAY * Math.pow(2, wsReconnectAttempts)
          wsReconnectAttempts++
          ws = null
          wsReconnectTimer = setTimeout(() => {
            connectWs().catch(() => {})
          }, delay)
        }
      }

      socket.onerror = () => {
        if (socket.readyState !== WebSocket.OPEN) {
          reject(new Error('WebSocket 连接失败'))
        }
      }
    })
  }

  function closeWs() {
    wsManualClose = true
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }
    wsReconnectAttempts = MAX_RECONNECT_ATTEMPTS
    handler = null
    if (ws) {
      ws.close()
      ws = null
    }
  }

  // ========== tool ack（WebSocket） ==========
  function sendToolAck(actionType: string, success: boolean, data?: ToolAckPayload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'tool_ack', action_type: actionType, success, data }))
    }
  }

  function registerToolAction(action: ToolCallAction) {
    pendingAction.value = action
    pendingActionAcked.value = false
    pendingActionExecuting.value = false
  }

  function claimPendingAction(action: ToolCallAction) {
    if (
      !pendingAction.value ||
      pendingAction.value !== action ||
      pendingActionAcked.value ||
      pendingActionExecuting.value
    ) {
      return false
    }
    pendingActionExecuting.value = true
    return true
  }

  function completePendingAction(action: ToolCallAction, success: boolean, data?: ToolAckPayload) {
    if (!pendingAction.value || pendingAction.value !== action || pendingActionAcked.value) {
      return false
    }
    pendingActionAcked.value = true
    pendingActionExecuting.value = false
    sendToolAck(action.type, success, data)
    pendingAction.value = null
    return true
  }

  // ========== 停止生成 ==========
  function stopGeneration() {
    if (handler) {
      handler.onDone()
      handler = null
    }
    sending.value = false
    pendingAction.value = null
    pendingActionAcked.value = false
    pendingActionExecuting.value = false
  }

  // ========== 执行/拒绝 action ==========
  function executeAction(action: ToolCallAction) {
    return action
  }
  function rejectAction() {
    pendingAction.value = null
    pendingActionAcked.value = false
    pendingActionExecuting.value = false
  }
  function grantNavigationPermission() {
    navigationPermissionGranted.value = true
    try { localStorage.setItem(NAV_PERMISSION_KEY, '1') } catch { /* */ }
  }

  async function ensureCurrentUser() {
    const auth = useAuthStore()
    if (auth.token && !auth.user) {
      await auth.fetchUserProfile()
    }
    if (!auth.user) {
      throw new Error('请先登录后再使用 AI 导购助手')
    }
    bindActiveUser(auth.user.id)
    return auth.user
  }
  // ========== 开场白 ==========
  const WELCOME_TEXT = `你好！我是 AI 导购助手 👋

  我可以帮你：
  • 浏览和搜索超市商品
  • 管理购物车，一键下单
  • 查看历史订单
  • 根据你的偏好推荐好物
  • 直接操控页面，带你跳转到对应功能

  试试对我说"帮我看看有什么饮料"或者"我购物车里有什么"吧～`

  function setWelcomeMessage() {
    messages.value = [{
      id: Date.now(),
      role: 'assistant',
      content: WELCOME_TEXT,
      time: formatTime(new Date()),
    }]
  }

  function resetConversationState() {
    stopGeneration()
    closeWs()
    messages.value = []
    pendingAction.value = null
    pendingActionAcked.value = false
    pendingActionExecuting.value = false
    sessionId.value = null
    sessions.value = []
    initialized.value = false
  }

  function resetState() {
    resetConversationState()
    activeUserId.value = null
  }

  function bindActiveUser(userId: number) {
    if (activeUserId.value === userId) return
    resetConversationState()
    activeUserId.value = userId
  }

  function executeClick(payload: unknown): boolean {
    const selector = (payload as { selector?: string })?.selector
    if (!selector) return false
    try {
      const el = document.querySelector(selector)
      if (el instanceof HTMLElement) { el.click(); return true }
      return false
    } catch { return false }
  }

  // ========== 接口1: 创建会话（HTTP） ==========
  async function createSession(): Promise<string> {
    const auth = useAuthStore()
    const user = await ensureCurrentUser()
    const res = await createSessionApi({
      user_id: user.id,
      username: user.username || auth.username || '',
    })
    const { session_id: sid, is_existing } = res.data.data
    sessionId.value = sid
    if (is_existing) {
      await loadSession(sid)
    } else {
      setWelcomeMessage()
    }
    return sid
  }

  // ========== 接口2: 查询所有会话（HTTP） ==========
  async function listSessions(): Promise<SessionInfo[]> {
    const user = await ensureCurrentUser()
    const res = await listSessionsApi({ user_id: user.id })
    const list = res.data.data.sessions || []
    sessions.value = list
    return list
  }

  // ========== 接口3: 加载会话消息（HTTP） ==========
  async function loadSession(sid: string): Promise<void> {
    const user = await ensureCurrentUser()
    const res = await loadSessionApi(sid, { user_id: user.id })
    if (res.data.data.missing) {
      if (sid === sessionId.value) sessionId.value = null
      setWelcomeMessage()
      await listSessions().catch(() => {})
      return
    }

    const list = res.data.data.messages as SessionMessage[] | undefined
    if (list && list.length > 0) {
      messages.value = list.map((m, i) => ({
        id: Date.now() + i,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        time: m.time || '',
        action: m.action as ToolCallAction | undefined,
      }))
    } else {
      setWelcomeMessage()
    }
  }

  // ========== 接口4: 删除会话（HTTP） ==========
  async function deleteSession(sid: string): Promise<void> {
    const user = await ensureCurrentUser()
    await deleteSessionApi(sid, { user_id: user.id })
    sessions.value = sessions.value.filter(s => s.session_id !== sid)
    // 如果删除的是当前会话，切换到其他会话或创建新会话
    if (sid === sessionId.value) {
      stopGeneration()
      pendingAction.value = null
      sessionId.value = null
      const remaining = sessions.value.find(s => s.session_id !== sid)
      if (remaining) {
        await switchSession(remaining.session_id)
        return
      }
      setWelcomeMessage()
    }
    await listSessions()
  }

  // ========== 切换会话 ==========
  async function switchSession(sid: string) {
    if (sid === sessionId.value) return
    stopGeneration()
    messages.value = []
    pendingAction.value = null
    sessionId.value = sid
    await loadSession(sid)
  }

  // ========== 发送消息（WebSocket 流式） ==========
  async function sendMessage(text: string) {
    if (!text.trim() || sending.value) return

    if (!sessionId.value) {
      try { await createSession() } catch {
        messages.value.push({
          id: Date.now(), role: 'assistant',
          content: '创建会话失败，请检查后端服务',
          time: formatTime(new Date()),
        })
        return
      }
    }

    stopGeneration()

    messages.value.push({
      id: Date.now(), role: 'user', content: text.trim(), time: formatTime(new Date()),
    })

    const assistantMsgId = Date.now() + 1
    messages.value.push({
      id: assistantMsgId, role: 'assistant', content: '', time: formatTime(new Date()),
    })
    sending.value = true

    let streamDone = false
    let streamError = ''

    function getAssistantMessage() {
      return messages.value.find(m => m.id === assistantMsgId)
    }

    function updateAssistantMessage(
      patch: Partial<AssistantMessage> | ((message: AssistantMessage) => Partial<AssistantMessage>),
    ) {
      const idx = messages.value.findIndex(m => m.id === assistantMsgId)
      if (idx < 0) return
      const current = messages.value[idx]
      const nextPatch = typeof patch === 'function' ? patch(current) : patch
      messages.value[idx] = { ...current, ...nextPatch }
    }

    handler = {
      onToken(content: string) {
        updateAssistantMessage(msg => ({ content: msg.content + content }))
        nextTick()
      },
      onDone() { streamDone = true },
      onError(err: string) { streamError = err; streamDone = true },
      onToolCall(action: ToolCallAction) {
        updateAssistantMessage({ action })
        registerToolAction(action)
      },
    }

    const timeoutId = setTimeout(() => {
      if (handler) { handler.onError('请求超时，请检查后端服务是否正常运行'); handler = null }
    }, AGENT_RESPONSE_TIMEOUT)

    try {
      const auth = useAuthStore()
      const user = await ensureCurrentUser()
      await connectWs()
      if (!handler) {
        streamDone = true
        if (!getAssistantMessage()?.content) {
          updateAssistantMessage({ content: streamError || '已中断生成' })
        }
        return
      }

      ws!.send(JSON.stringify({
        type: 'chat',
        session_id: sessionId.value,
        message: text.trim(),
        user_id: user.id,
        username: user.username || auth.username || '',
      }))

      while (!streamDone && !streamError) {
        await new Promise((r) => setTimeout(r, 100))
      }

      if (streamError && !getAssistantMessage()?.content) {
        updateAssistantMessage({ content: streamError })
      }
      const latestAssistantMsg = getAssistantMessage()
      if (!latestAssistantMsg?.content && !latestAssistantMsg?.action) {
        updateAssistantMessage({ content: 'AI 未返回有效内容，请稍后重试' })
      }
    } catch {
      if (!getAssistantMessage()?.content) {
        updateAssistantMessage({ content: '网络异常，请检查后端服务是否已启动' })
      }
    } finally {
      clearTimeout(timeoutId)
      sending.value = false
      const latestAssistantMsg = getAssistantMessage()
      if (!latestAssistantMsg?.content && !latestAssistantMsg?.action) {
        const idx = messages.value.findIndex(m => m.id === assistantMsgId)
        if (idx > -1) messages.value.splice(idx, 1)
      }
      if (sessionId.value) {
        await listSessions().catch(() => {})
      }
    }
  }

  // ========== 新建会话（UI 触发） ==========
  async function newSession() {
    stopGeneration()
    pendingAction.value = null
    sessionId.value = null
    setWelcomeMessage()
  }

  // ========== 初始化（页面挂载时调用） ==========
  async function init() {
    if (sending.value) {
      await listSessions().catch(() => {})
      initialized.value = true
      return
    }
    if (initialized.value && (sessionId.value || messages.value.length > 0)) {
      await listSessions().catch(() => {})
      return
    }
    try {
      await listSessions()
      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0].session_id)
      } else {
        sessionId.value = null
        setWelcomeMessage()
      }
      initialized.value = true
    } catch {
      sessionId.value = null
      setWelcomeMessage()
      initialized.value = true
    }
  }

  function destroy() {
    stopGeneration()
    closeWs()
  }

  return {
    messages, sending, widgetOpen, widgetMinimized, panelExpanded,
    pendingAction, navigationPermissionGranted,
    sessionId, sessions,
    sendMessage, stopGeneration,
    executeAction, rejectAction, grantNavigationPermission, claimPendingAction, completePendingAction,
    sendToolAck, executeClick,
    createSession, listSessions, loadSession, switchSession, deleteSession,
    newSession, init, destroy, resetState,
  }
})
