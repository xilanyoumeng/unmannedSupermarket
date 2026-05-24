<script setup lang="ts">
import { computed, ref, nextTick, watch, onMounted } from 'vue'
import { isNavigationFailure, NavigationFailureType, useRouter } from 'vue-router'
import { useAssistantStore, type ToolAckPayload, type ToolCallAction } from '../stores/assistant'

const router = useRouter()
const store = useAssistantStore()

const inputText = ref('')
const chatContainer = ref<HTMLElement | null>(null)

// 初始化：拉会话列表 → 进最近会话 或 创建新会话
onMounted(() => {
  store.init()
})

// 快捷指令
const quickActions = [
  { label: '🔥 今日热销', prompt: '帮我看看今天什么商品最热销' },
  { label: '🛒 我的购物车', prompt: '我购物车里有什么' },
  { label: '💰 推荐好物', prompt: '根据我的购物习惯推荐一些商品' },
  { label: '📦 查看订单', prompt: '帮我查一下最近的订单' },
  { label: '🏷️ 分类浏览', prompt: '有哪些商品分类' },
  { label: '💡 购物建议', prompt: '给我一些省钱的购物建议' },
]

// 自动滚动
async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const messageProgressKey = computed(() => {
  const last = store.messages[store.messages.length - 1]
  return [
    store.messages.length,
    last?.content || '',
    last?.action?.type || '',
    last?.action?.label || '',
    store.pendingAction?.type || '',
    store.pendingAction?.label || '',
    store.sending ? 'sending' : 'idle',
  ].join('|')
})

watch(messageProgressKey, scrollToBottom, { flush: 'post' })

// 发送
async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await store.sendMessage(text)
  await scrollToBottom()
}

function handleQuickAction(prompt: string) {
  inputText.value = prompt
  handleSend()
}

type ActionResult = {
  success: boolean
  data?: ToolAckPayload
}

const NAVIGATION_TIMEOUT_MS = 5000

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return String(error || '未知错误')
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      window.setTimeout(() => reject(new Error('前端路由跳转超时')), timeoutMs)
    }),
  ])
}

// 执行 tool action，发 ack 给 agent 使其继续推理
async function executeAndAck(action: ToolCallAction): Promise<ActionResult> {
  if (action.type === 'navigate' && action.payload) {
    const path = typeof action.payload === 'string' ? action.payload : ''
    if (!path) {
      return { success: false, data: { error: '缺少目标路由' } }
    }
    const resolved = router.resolve(path)
    if (!resolved.matched.length) {
      return { success: false, data: { error: `前端路由不存在: ${path}` } }
    }
    store.executeAction(action)
    try {
      const failure = await withTimeout(router.push(path), NAVIGATION_TIMEOUT_MS)
      if (
        failure &&
        isNavigationFailure(failure) &&
        !isNavigationFailure(failure, NavigationFailureType.duplicated)
      ) {
        return { success: false, data: { error: '前端路由跳转失败', requestedPath: path } }
      }
      const currentPath = router.currentRoute.value.fullPath
      if (router.currentRoute.value.name === 'Login' && path !== '/login') {
        return { success: false, data: { error: '跳转被登录态拦截', requestedPath: path, currentPath } }
      }
      store.grantNavigationPermission()
      return { success: true, data: { requestedPath: path, currentPath } }
    } catch (error) {
      return { success: false, data: { error: getErrorMessage(error), requestedPath: path } }
    }
  }
  if (action.type === 'click') {
    store.executeAction(action)
    const ok = store.executeClick(action.payload)
    return {
      success: ok,
      data: ok ? undefined : { error: '未找到或无法点击目标元素' },
    }
  }
  return { success: false, data: { error: `未知前端动作: ${action.type}` } }
}

async function executePendingAction(action: ToolCallAction) {
  if (!store.claimPendingAction(action)) return
  const result = await executeAndAck(action)
  store.completePendingAction(action, result.success, result.data)
}

// 用户手动确认
function handleAction(action: ToolCallAction) {
  void executePendingAction(action)
}

function handleRejectAction() {
  const action = store.pendingAction
  if (action) {
    if (!store.claimPendingAction(action)) return
    store.completePendingAction(action, false)
  }
}

// 已授权导航 / click 动作：tool_call 到达时立即执行，并把真实结果回传给后端
watch(() => store.pendingAction, (action) => {
  if (!action) return
  // navigate: 首次使用需要用户确认，之后按授权自动执行
  if (action.type === 'navigate') {
    if (!store.navigationPermissionGranted) store.grantNavigationPermission()
    void executePendingAction(action)
    return
  }
  // click: 始终自动执行
  if (action.type === 'click') {
    void executePendingAction(action)
  }
}, { flush: 'sync' })

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="assistant-page">
    <div class="assistant-layout">
      <!-- 左侧：聊天主区域 -->
      <div class="chat-panel">
        <!-- 顶部标题栏 -->
        <div class="chat-header">
          <div class="chat-header-info">
            <span class="chat-avatar">🤖</span>
            <div>
              <div class="chat-title">AI 导购助手</div>
              <div class="chat-subtitle">智能推荐 · 对话购物 · 页面操控</div>
            </div>
            <el-tag v-if="store.sending" size="small" type="warning" class="chat-status-tag">
              回复中
            </el-tag>
          </div>
          <el-button text type="primary" @click="store.newSession()">
            ➕ 新建会话
          </el-button>
        </div>

        <!-- 消息列表 -->
        <div ref="chatContainer" class="chat-messages">
          <template v-for="msg in store.messages" :key="msg.id">
            <!-- 发送中时隐藏空内容气泡 -->
            <div
              v-if="msg.content || !store.sending"
              class="message-row"
              :class="msg.role === 'user' ? 'message-row--user' : 'message-row--assistant'"
            >
            <!-- AI 头像 -->
            <div v-if="msg.role === 'assistant'" class="message-avatar">🤖</div>

            <div class="message-body" :class="'message-body--' + msg.role">
              <div class="message-text" v-text="msg.content" />

              <!-- Tool call 操作条 -->
              <div v-if="msg.action && msg.role === 'assistant'" class="message-action-bar">
                <span class="action-label">🔗 {{ msg.action.label }}</span>
                <div v-if="msg.action.type === 'navigate' && !store.navigationPermissionGranted" class="action-btns">
                  <el-button size="small" type="primary" @click="handleAction(msg.action!)">确认</el-button>
                  <el-button size="small" @click="handleRejectAction">拒绝</el-button>
                </div>
              </div>

              <div class="message-time">{{ msg.time }}</div>
            </div>

            <!-- 用户头像 -->
            <div v-if="msg.role === 'user'" class="message-avatar">👤</div>
          </div>
        </template>

          <!-- 加载动画：仅在等待首字符时显示 -->
          <div
            v-if="store.sending && store.messages.length > 0 && !store.messages[store.messages.length - 1].content"
            class="message-row message-row--assistant"
          >
            <div class="message-avatar">🤖</div>
            <div class="message-body message-body--assistant">
              <div class="typing-dots">
                <span /><span /><span />
              </div>
            </div>
          </div>
        </div>

        <!-- Tool call 待确认栏（与悬浮窗保持一致） -->
        <div
          v-if="store.pendingAction && store.pendingAction.type === 'navigate' && !store.navigationPermissionGranted"
          class="pending-action-bar"
        >
          <span>🔗 AI 想要：<strong>{{ store.pendingAction.label }}</strong></span>
          <div class="action-btns">
            <el-button size="small" type="primary" @click="handleAction(store.pendingAction!)">
              确认
            </el-button>
            <el-button size="small" @click="handleRejectAction">拒绝</el-button>
          </div>
        </div>

        <!-- 快捷指令 -->
        <div class="quick-actions">
          <el-button
            v-for="qa in quickActions"
            :key="qa.label"
            size="small"
            round
            class="quick-chip"
            @click="handleQuickAction(qa.prompt)"
          >
            {{ qa.label }}
          </el-button>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            placeholder="输入您的问题..."
            :disabled="store.sending"
            resize="none"
            class="chat-input"
            @keydown="handleKeydown"
          />
          <el-button
            v-if="!store.sending"
            type="primary"
            :disabled="!inputText.trim()"
            class="send-btn"
            @click="handleSend"
          >
            发送
          </el-button>
          <el-button
            v-else
            type="danger"
            class="send-btn"
            @click="store.stopGeneration()"
          >
            ⏹ 停止
          </el-button>
        </div>
      </div>

      <!-- 右侧：信息面板 -->
      <div class="info-panel">
        <!-- 历史会话 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <div class="info-card-header-row">
              <span class="info-card-title">💬 历史会话</span>
              <el-button size="small" text type="primary" @click="store.newSession()">
                ＋新建
              </el-button>
            </div>
          </template>
          <div class="session-list" v-if="store.sessions.length > 0">
            <div
              v-for="s in store.sessions"
              :key="s.session_id"
              class="session-item"
              :class="{ 'session-item--active': s.session_id === store.sessionId }"
              @click="store.switchSession(s.session_id)"
            >
              <div class="session-item-content">
                <div class="session-title">{{ s.title || '新会话' }}</div>
                <div class="session-meta">
                  <span>{{ s.created_at?.slice(0, 10) }}</span>
                  <span v-if="s.last_message" class="session-last">{{ s.last_message }}</span>
                </div>
              </div>
              <el-button
                class="session-delete-btn"
                size="small"
                text
                type="danger"
                @click.stop="store.deleteSession(s.session_id)"
              >
                🗑
              </el-button>
            </div>
          </div>
          <div v-else class="session-empty">暂无历史会话</div>
        </el-card>

        <!-- 快捷入口 -->
        <el-card class="info-card" shadow="never">
          <template #header>
            <span class="info-card-title">⚡ 快捷入口</span>
          </template>
          <div class="shortcut-list">
            <el-button class="shortcut-btn" @click="router.push('/shopping')">
              🛒 智慧购物
            </el-button>
            <el-button class="shortcut-btn" @click="router.push('/cart')">
              🛍️ 购物车
            </el-button>
            <el-button class="shortcut-btn" @click="router.push('/profile')">
              👤 个人中心
            </el-button>
            <el-button class="shortcut-btn" @click="router.push('/')">
              🏠 首页
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.assistant-page {
  animation: fadeIn 0.25s;
  height: calc(100vh - 140px);
  min-height: 560px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.assistant-layout {
  display: flex;
  gap: 20px;
  height: 100%;
}

/* ===== 聊天面板 ===== */
.chat-panel {
  flex: 1;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.chat-header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-status-tag {
  margin-left: 4px;
}

.chat-avatar {
  font-size: 2rem;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0e8ff 100%);
  border-radius: 14px;
}

.chat-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #1F2A3E;
}

.chat-subtitle {
  font-size: 0.75rem;
  color: #999;
  margin-top: 2px;
}

/* ===== 消息区域 ===== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-messages::-webkit-scrollbar {
  width: 5px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #e0e0e0;
  border-radius: 10px;
}

.message-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  max-width: 85%;
}

.message-row--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-row--assistant {
  align-self: flex-start;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
  background: #f5f5f5;
}

.message-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-body--user {
  align-items: flex-end;
}

.message-body--assistant {
  align-items: flex-start;
}

.message-text {
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-line;
  word-break: break-word;
}

.message-row--user .message-text {
  background: linear-gradient(135deg, #1677FF, #4096ff);
  color: #fff;
  border-bottom-right-radius: 6px;
}

.message-row--assistant .message-text {
  background: #f5f6f8;
  color: #1F2A3E;
  border-bottom-left-radius: 6px;
}

.message-time {
  font-size: 0.7rem;
  color: #bbb;
  padding: 0 4px;
}

/* ===== Tool call 操作条 ===== */
.message-action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fff8e1;
  border-radius: 12px;
  border: 1px solid #ffe082;
  flex-wrap: wrap;
}

.action-label {
  font-size: 0.8rem;
  color: #666;
}

.action-btns {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.pending-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 20px;
  background: #fff8e1;
  border-top: 1px solid #ffe082;
  font-size: 0.84rem;
  flex-shrink: 0;
}

/* ===== 加载动画 ===== */
.typing-dots {
  display: flex;
  gap: 5px;
  padding: 12px 16px;
  background: #f5f6f8;
  border-radius: 18px;
  border-bottom-left-radius: 6px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c0c0;
  animation: dotBounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
.typing-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ===== 快捷指令 ===== */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.quick-chip {
  font-size: 0.78rem;
}

/* ===== 输入区域 ===== */
.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 20px 16px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 14px;
  padding: 10px 16px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.send-btn {
  border-radius: 14px;
  height: 40px;
  padding: 0 24px;
  flex-shrink: 0;
}

/* ===== 右侧信息面板 ===== */
.info-panel {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  border-radius: 16px;
}

.info-card :deep(.el-card__header) {
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
}

.info-card :deep(.el-card__body) {
  padding: 12px 16px 16px;
}

.info-card-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1F2A3E;
}

.capability-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.capability-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.capability-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
  margin-top: 1px;
}

.capability-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: #333;
}

.capability-desc {
  font-size: 0.72rem;
  color: #999;
  margin-top: 1px;
}

.info-card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ===== 会话列表 ===== */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 260px;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-item:hover {
  background: #f5f6f8;
}

.session-item--active {
  background: #e8f4ff;
}

.session-item-content {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.session-delete-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
  font-size: 0.85rem;
  padding: 4px;
}

.session-item:hover .session-delete-btn {
  opacity: 1;
}

.session-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: #1F2A3E;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #aaa;
  margin-top: 3px;
}

.session-last {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
}

.session-empty {
  text-align: center;
  color: #ccc;
  font-size: 0.8rem;
  padding: 20px 0;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-btn {
  width: 100%;
  justify-content: flex-start;
  border-radius: 12px;
  font-size: 0.82rem;
}

/* ===== 夜间模式 ===== */
html.dark .chat-panel {
  background: #1a1a1a;
}

html.dark .chat-header {
  border-bottom-color: #2a2a2a;
}

html.dark .chat-title {
  color: #e0e0e0;
}

html.dark .message-row--assistant .message-text {
  background: #2a2a2a;
  color: #e0e0e0;
}

html.dark .chat-input-area,
html.dark .quick-actions {
  border-top-color: #2a2a2a;
}

html.dark .info-card {
  background: #1a1a1a;
  border-color: #2a2a2a;
}

html.dark .info-card :deep(.el-card__header) {
  border-bottom-color: #2a2a2a;
}

html.dark .info-card-title {
  color: #e0e0e0;
}

html.dark .capability-name {
  color: #ccc;
}

html.dark .typing-dots {
  background: #2a2a2a;
}

html.dark .message-avatar {
  background: #2a2a2a;
}

html.dark .chat-avatar {
  background: linear-gradient(135deg, #1a2740 0%, #2a1f3a 100%);
}

html.dark .message-action-bar {
  background: #2a2010;
  border-color: #4a3800;
}

html.dark .pending-action-bar {
  background: #2a2010;
  border-top-color: #4a3800;
}

html.dark .session-item:hover {
  background: #2a2a2a;
}

html.dark .session-item--active {
  background: #1a2740;
}

html.dark .session-item:hover .session-delete-btn {
  opacity: 1;
}

html.dark .session-title {
  color: #e0e0e0;
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .assistant-page {
    height: auto;
    min-height: 80vh;
  }

  .assistant-layout {
    flex-direction: column;
  }

  .info-panel {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .info-card {
    flex: 1;
    min-width: 200px;
  }

  .message-row {
    max-width: 92%;
  }
}
</style>
