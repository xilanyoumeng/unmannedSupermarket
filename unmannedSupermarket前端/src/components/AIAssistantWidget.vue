<script setup lang="ts">
import { computed, ref, watch, nextTick, onUnmounted } from 'vue'
import { isNavigationFailure, NavigationFailureType, useRouter } from 'vue-router'
import { useAssistantStore, type ToolAckPayload, type ToolCallAction } from '../stores/assistant'

const router = useRouter()
const store = useAssistantStore()

const inputText = ref('')
const msgContainer = ref<HTMLElement | null>(null)
const widgetRef = ref<HTMLElement | null>(null)

// 展开状态：null=关闭, 'mini'=最小化, 'chat'=对话窗口, 'panel'=大面板
const mode = ref<'mini' | 'chat' | 'panel' | null>(null)
const lastMode = ref<'chat' | 'panel'>('chat')
const dragPosition = ref<{ left: number; top: number } | null>(null)
const dragging = ref(false)
const dragMoved = ref(false)
const dragMoveThreshold = 4
let dragStart = {
  pointerId: 0,
  x: 0,
  y: 0,
  left: 0,
  top: 0,
}

// 自动滚动
async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
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

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
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

// 打开/关闭
function openChat() {
  mode.value = 'chat'
  lastMode.value = 'chat'
  normalizeWidgetPosition()
}

function openPanel() {
  mode.value = 'panel'
  lastMode.value = 'panel'
  normalizeWidgetPosition()
}

function closeWidget() {
  mode.value = null
  store.stopGeneration()
}

onUnmounted(() => {
  store.destroy()
})

function toggleMini() {
  if (mode.value === 'mini') {
    mode.value = lastMode.value
  } else {
    lastMode.value = mode.value === 'chat' ? 'chat' : 'panel'
    mode.value = 'mini'
  }
  normalizeWidgetPosition()
}

const widgetStyle = computed(() => {
  if (!dragPosition.value) return {}
  return {
    left: `${dragPosition.value.left}px`,
    top: `${dragPosition.value.top}px`,
    right: 'auto',
    bottom: 'auto',
  }
})

function clampPosition(left: number, top: number, width: number, height: number) {
  const margin = 8
  const maxLeft = Math.max(margin, window.innerWidth - width - margin)
  const maxTop = Math.max(margin, window.innerHeight - height - margin)
  return {
    left: Math.min(Math.max(left, margin), maxLeft),
    top: Math.min(Math.max(top, margin), maxTop),
  }
}

function normalizeWidgetPosition() {
  nextTick(() => {
    if (!dragPosition.value) return
    const el = widgetRef.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    dragPosition.value = clampPosition(rect.left, rect.top, rect.width, rect.height)
  })
}

function handleDragStart(e: PointerEvent) {
  if (e.button !== 0) return
  const target = e.target as HTMLElement
  if (target.closest('.ai-widget-header-actions')) return
  const el = widgetRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const start = clampPosition(rect.left, rect.top, rect.width, rect.height)
  dragging.value = true
  dragMoved.value = false
  dragStart = {
    pointerId: e.pointerId,
    x: e.clientX,
    y: e.clientY,
    left: start.left,
    top: start.top,
  }
  el.setPointerCapture(e.pointerId)
  e.preventDefault()
}

function handleDragMove(e: PointerEvent) {
  if (!dragging.value || e.pointerId !== dragStart.pointerId) return
  const el = widgetRef.value
  if (!el) return
  const dx = e.clientX - dragStart.x
  const dy = e.clientY - dragStart.y
  if (!dragMoved.value) {
    if (Math.abs(dx) < dragMoveThreshold && Math.abs(dy) < dragMoveThreshold) return
    dragMoved.value = true
  }
  const rect = el.getBoundingClientRect()
  dragPosition.value = clampPosition(
    dragStart.left + dx,
    dragStart.top + dy,
    rect.width,
    rect.height,
  )
}

function finishDrag(e: PointerEvent) {
  if (!dragging.value || e.pointerId !== dragStart.pointerId) return
  const moved = dragMoved.value
  dragging.value = false
  dragMoved.value = false
  const el = widgetRef.value
  if (el?.hasPointerCapture(e.pointerId)) {
    el.releasePointerCapture(e.pointerId)
  }
  return moved
}

function handleDragEnd(e: PointerEvent) {
  finishDrag(e)
}

function handleFabPointerUp(e: PointerEvent) {
  const moved = finishDrag(e)
  if (moved === false) {
    openChat()
  }
}

function handleMiniPointerUp(e: PointerEvent) {
  const moved = finishDrag(e)
  if (moved === false) {
    toggleMini()
  }
}
</script>

<template>
  <!-- 关闭态：浮动按钮 -->
  <div
    v-if="!mode"
    ref="widgetRef"
    class="ai-fab"
    :class="{ 'ai-floating--dragging': dragging }"
    :style="widgetStyle"
    @pointerdown="handleDragStart"
    @pointermove="handleDragMove"
    @pointerup="handleFabPointerUp"
    @pointercancel="handleDragEnd"
  >
    <span>🤖</span>
  </div>

  <!-- 最小化态：小条 -->
  <div
    v-else-if="mode === 'mini'"
    ref="widgetRef"
    class="ai-mini-bar"
    :class="{ 'ai-floating--dragging': dragging }"
    :style="widgetStyle"
    @pointerdown="handleDragStart"
    @pointermove="handleDragMove"
    @pointerup="handleMiniPointerUp"
    @pointercancel="handleDragEnd"
  >
    <span>🤖</span>
    <span v-if="store.sending" class="ai-mini-status">回复中...</span>
    <span v-else class="ai-mini-label">AI 导购助手</span>
  </div>

  <!-- 对话窗 / 大面板 -->
  <div
    v-else
    ref="widgetRef"
    class="ai-widget"
    :class="{ 'ai-widget--panel': mode === 'panel', 'ai-widget--dragging': dragging }"
    :style="widgetStyle"
    @pointermove="handleDragMove"
    @pointerup="handleDragEnd"
    @pointercancel="handleDragEnd"
  >
    <!-- 标题栏 -->
    <div class="ai-widget-header" @pointerdown="handleDragStart">
      <div class="ai-widget-title">
        <span>🤖</span>
        <span class="ai-widget-title-text">AI 导购助手</span>
        <el-tag v-if="store.sending" size="small" type="warning" class="ai-status-tag">
          回复中
        </el-tag>
      </div>
      <div class="ai-widget-header-actions">
        <el-button
          v-if="mode !== 'panel'"
          size="small"
          text
          @click="openPanel"
          title="展开面板"
        >⛶</el-button>
        <el-button
          v-else
          size="small"
          text
          @click="openChat"
          title="收起面板"
        >🗗</el-button>
        <el-button size="small" text @click="store.newSession()" title="新建会话">＋</el-button>
        <el-button size="small" text @click="toggleMini" title="最小化">—</el-button>
        <el-button size="small" text @click="closeWidget" title="关闭">✕</el-button>
      </div>
    </div>

    <!-- 消息区 -->
    <div ref="msgContainer" class="ai-widget-messages">
      <template v-for="msg in store.messages" :key="msg.id">
        <!-- 发送中时隐藏空内容气泡，避免和加载点双头像 -->
        <div
          v-if="msg.content || !store.sending"
          class="ai-widget-msg"
          :class="'ai-widget-msg--' + msg.role"
        >
          <div class="ai-widget-bubble" :class="'ai-widget-bubble--' + msg.role">
            <div class="ai-widget-text">{{ msg.content }}</div>

            <div v-if="msg.action && msg.role === 'assistant'" class="ai-action-bar">
              <span class="ai-action-desc">🔗 {{ msg.action.label }}</span>
              <div v-if="msg.action.type === 'navigate' && !store.navigationPermissionGranted" class="ai-action-btns">
                <el-button size="small" type="primary" @click="handleAction(msg.action!)">
                  确认
                </el-button>
                <el-button size="small" @click="handleRejectAction">拒绝</el-button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 加载动画：仅在等待首字符时显示，文字开始输出后隐藏 -->
      <div
        v-if="store.sending && store.messages.length > 0 && !store.messages[store.messages.length - 1].content"
        class="ai-widget-msg ai-widget-msg--assistant"
      >
        <div class="ai-widget-bubble ai-widget-bubble--assistant">
          <div class="ai-typing-dots"><span /><span /><span /></div>
        </div>
      </div>
    </div>

    <!-- Tool call 待确认栏（全局底部，已授权/click 自动执行不展示） -->
    <div v-if="store.pendingAction && store.pendingAction.type === 'navigate' && !store.navigationPermissionGranted" class="ai-pending-action-bar">
      <span>🔗 AI 想要：<strong>{{ store.pendingAction.label }}</strong></span>
      <div class="ai-action-btns">
        <el-button size="small" type="primary" @click="handleAction(store.pendingAction!)">
          确认
        </el-button>
        <el-button size="small" @click="handleRejectAction">拒绝</el-button>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="ai-widget-input-area">
      <el-input
        v-model="inputText"
        placeholder="输入问题..."
        :disabled="store.sending"
        class="ai-widget-input"
        size="small"
        @keydown="handleKeydown"
      />
      <el-button
        v-if="!store.sending"
        type="primary"
        size="small"
        :disabled="!inputText.trim()"
        @click="handleSend"
      >
        发送
      </el-button>
      <el-button
        v-else
        type="danger"
        size="small"
        @click="store.stopGeneration()"
      >
        ⏹ 停止
      </el-button>
    </div>
  </div>
</template>

<style scoped>
/* ===== FAB 浮动按钮 ===== */
.ai-fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677FF, #4096ff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  cursor: grab;
  box-shadow: 0 4px 20px rgba(22, 119, 255, 0.35);
  z-index: 999;
  transition: transform 0.2s, box-shadow 0.2s;
  user-select: none;
  touch-action: none;
}

.ai-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(22, 119, 255, 0.45);
}

.ai-fab.ai-floating--dragging,
.ai-fab.ai-floating--dragging:hover {
  cursor: grabbing;
  transform: none;
}

/* ===== 最小化条 ===== */
.ai-mini-bar {
  position: fixed;
  bottom: 28px;
  right: 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border-radius: 24px;
  padding: 10px 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  cursor: grab;
  z-index: 999;
  font-size: 0.9rem;
  transition: box-shadow 0.2s;
  user-select: none;
  touch-action: none;
}

.ai-mini-bar:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
}

.ai-mini-bar.ai-floating--dragging {
  cursor: grabbing;
}

.ai-mini-status {
  color: #1677FF;
  font-weight: 600;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.ai-mini-label {
  color: #666;
}

/* ===== 浮动窗口 ===== */
.ai-widget {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 420px;
  max-height: 600px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  z-index: 999;
  overflow: hidden;
  animation: slideUp 0.25s ease-out;
}

.ai-widget--dragging {
  user-select: none;
}

.ai-widget--panel {
  width: 520px;
  max-height: 720px;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 标题栏 */
.ai-widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, #e8f4ff 0%, #f0e8ff 100%);
  flex-shrink: 0;
  cursor: grab;
  touch-action: none;
}

.ai-widget--dragging .ai-widget-header {
  cursor: grabbing;
}

.ai-widget-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-widget-title-text {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1F2A3E;
}

.ai-status-tag {
  margin-left: 4px;
}

.ai-widget-header-actions {
  display: flex;
  gap: 2px;
  cursor: default;
}

/* 消息区 */
.ai-widget-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 340px;
}

.ai-widget--panel .ai-widget-messages {
  max-height: 460px;
}

.ai-widget-messages::-webkit-scrollbar {
  width: 4px;
}

.ai-widget-messages::-webkit-scrollbar-thumb {
  background: #e0e0e0;
  border-radius: 10px;
}

.ai-widget-msg {
  display: flex;
  max-width: 90%;
}

.ai-widget-msg--user {
  align-self: flex-end;
}

.ai-widget-msg--assistant {
  align-self: flex-start;
}

.ai-widget-bubble {
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 0.82rem;
  line-height: 1.55;
  white-space: pre-line;
  word-break: break-word;
}

.ai-widget-bubble--user {
  background: linear-gradient(135deg, #1677FF, #4096ff);
  color: #fff;
  border-bottom-right-radius: 6px;
}

.ai-widget-bubble--assistant {
  background: #f5f6f8;
  color: #1F2A3E;
  border-bottom-left-radius: 6px;
}

.ai-widget-text {
  min-height: 2px;
}

/* Tool call 操作条 */
.ai-action-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.ai-action-desc {
  font-size: 0.78rem;
  color: #666;
}

.ai-action-btns {
  display: flex;
  gap: 6px;
}

/* 底部待确认栏 */
.ai-pending-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 16px;
  background: #fff8e1;
  border-top: 1px solid #ffe082;
  font-size: 0.82rem;
  flex-shrink: 0;
}

/* 输入区 */
.ai-widget-input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px 14px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.ai-widget-input {
  flex: 1;
}

/* 加载动画 */
.ai-typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.ai-typing-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c0c0c0;
  animation: dotBounce 1.4s infinite ease-in-out both;
}

.ai-typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.ai-typing-dots span:nth-child(2) { animation-delay: -0.16s; }
.ai-typing-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ===== 夜间模式 ===== */
html.dark .ai-widget {
  background: #1e1e1e;
}

html.dark .ai-mini-bar {
  background: #1e1e1e;
}

html.dark .ai-mini-label {
  color: #aaa;
}

html.dark .ai-widget-header {
  background: linear-gradient(135deg, #1a2740 0%, #2a1f3a 100%);
}

html.dark .ai-widget-title-text {
  color: #e0e0e0;
}

html.dark .ai-widget-bubble--assistant {
  background: #2a2a2a;
  color: #e0e0e0;
}

html.dark .ai-typing-dots span {
  background: #555;
}

html.dark .ai-widget-input-area {
  border-top-color: #2a2a2a;
}

html.dark .ai-pending-action-bar {
  background: #2a2010;
  border-top-color: #4a3800;
}

html.dark .ai-action-desc {
  color: #aaa;
}

html.dark .ai-action-bar {
  border-top-color: rgba(255, 255, 255, 0.08);
}

@media (max-width: 500px) {
  .ai-widget {
    width: calc(100vw - 24px);
    right: 12px;
    bottom: 12px;
    max-height: 70vh;
  }

  .ai-widget--panel {
    width: calc(100vw - 24px);
    max-height: 85vh;
  }
}
</style>
