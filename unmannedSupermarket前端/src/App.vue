<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { isNavigationFailure, NavigationFailureType, useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useCartStore } from './stores/cart'
import { useAssistantStore, type ToolAckPayload, type ToolCallAction } from './stores/assistant'
import AIAssistantWidget from './components/AIAssistantWidget.vue'
import AIToolPromptDialog from './components/AIToolPromptDialog.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const cartStore = useCartStore()
const assistantStore = useAssistantStore()
const NAVIGATION_TIMEOUT_MS = 5000

const isLoginPage = computed(() => route.name === 'Login')
const isDark = ref(localStorage.getItem('theme') === 'dark')

// 将任意路由路径映射到最接近的菜单项，避免 el-menu default-active 拿到无效值后卡死
const MENU_ROUTES = ['/', '/shopping', '/assistant', '/cart', '/profile', '/admin']
const activeMenu = computed(() => {
  const path = route.path
  // 精确匹配
  if (MENU_ROUTES.includes(path)) return path
  // 前缀匹配（如 /order-confirm/123 不匹配任何菜单项，返回空让菜单不选中）
  const matched = MENU_ROUTES.find(r => r !== '/' && path.startsWith(r))
  return matched || ''
})

onMounted(() => {
  if (authStore.token) {
    authStore.fetchUserProfile()
  }
})

watch(() => authStore.user?.id ?? null, (newUserId, oldUserId) => {
  if (oldUserId !== null && newUserId !== oldUserId) {
    assistantStore.resetState()
  }
})

function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

function onMenuSelect(index: string) {
  if (!index) return
  // 避免重复导航到当前路由导致 Vue Router 取消导航卡死
  if (route.path === index) return
  router.push(index).catch(() => { /* 导航被取消（如同一个路由），忽略 */ })
}

type ActionResult = {
  success: boolean
  data?: ToolAckPayload
}

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

async function executeAssistantAction(action: ToolCallAction): Promise<ActionResult> {
  if (action.type === 'navigate' && action.payload) {
    const path = typeof action.payload === 'string' ? action.payload : ''
    if (!path) {
      return { success: false, data: { error: '缺少目标路由' } }
    }
    const resolved = router.resolve(path)
    if (!resolved.matched.length) {
      return { success: false, data: { error: `前端路由不存在: ${path}` } }
    }

    assistantStore.executeAction(action)
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
      assistantStore.grantNavigationPermission()
      return { success: true, data: { requestedPath: path, currentPath } }
    } catch (error) {
      return { success: false, data: { error: getErrorMessage(error), requestedPath: path } }
    }
  }

  if (action.type === 'click') {
    assistantStore.executeAction(action)
    const ok = assistantStore.executeClick(action.payload)
    return {
      success: ok,
      data: ok ? undefined : { error: '未找到或无法点击目标元素' },
    }
  }

  return { success: false, data: { error: `未知前端动作: ${action.type}` } }
}

async function executePendingAssistantAction(action: ToolCallAction) {
  if (!assistantStore.claimPendingAction(action)) return
  const result = await executeAssistantAction(action)
  assistantStore.completePendingAction(action, result.success, result.data)
}

watch(() => assistantStore.pendingAction, (action) => {
  if (!action) return
  if (action.type === 'navigate') {
    if (!assistantStore.navigationPermissionGranted) {
      assistantStore.grantNavigationPermission()
    }
    void executePendingAssistantAction(action)
    return
  }
  if (action.type === 'click') {
    void executePendingAssistantAction(action)
  }
}, { flush: 'sync' })

function handleLogout() {
  assistantStore.resetState()
  authStore.clearAuth()
  cartStore.resetCart()
  router.push('/login')
}
</script>

<template>
  <!-- 登录页直接渲染，无需导航栏 -->
  <template v-if="isLoginPage">
    <router-view />
  </template>

  <!-- 主应用布局（登录后） -->
  <template v-else>
    <div class="navbar-wrap">
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        class="app-navbar"
        @select="onMenuSelect"
      >
        <div class="logo-area">
          <span class="logo-icon">🔷</span>
          <span class="logo-text">眸界·无感智付</span>
        </div>

        <el-menu-item index="/">🏠 首页</el-menu-item>

        <el-menu-item index="/shopping">🛒 智慧购物</el-menu-item>
        <el-menu-item index="/assistant">🤖 AI导购助手</el-menu-item>
        <el-menu-item index="/cart">
          🛍️ 购物车
          <el-badge v-if="cartStore.totalCount" :value="cartStore.totalCount" class="cart-badge" />
        </el-menu-item>
        <el-menu-item index="/profile">👤 个人中心</el-menu-item>
        <el-menu-item v-if="authStore.isAdmin" index="/admin">📊 后台管理</el-menu-item>
      </el-menu>
    </div>

    <router-view />

    <!-- 右上角浮动工具栏：用户信息 + 退出（仅登录后） -->
    <div v-if="authStore.user" class="float-toolbar">
      <div class="user-float-card">
        <div class="user-float-avatar">👤</div>
        <span class="user-float-name">{{ authStore.username }}</span>
        <el-button
          size="small"
          class="logout-float-btn"
          @click="handleLogout"
        >
          退出登录
        </el-button>
      </div>
    </div>
  </template>

  <!-- AI 导购助手浮动组件：全局可见 -->
  <AIAssistantWidget v-if="authStore.isLoggedIn" />
  <AIToolPromptDialog v-if="authStore.isLoggedIn" />

  <!-- 日夜间切换：全局可见 -->
  <div class="theme-float-wrap">
    <el-button
      size="small"
      circle
      class="theme-float-btn"
      @click="toggleTheme"
    >
      {{ isDark ? '☀️' : '🌙' }}
    </el-button>
  </div>
</template>

<style scoped>
.navbar-wrap {
  margin: 20px 0 28px;
}

.app-navbar {
  border-radius: 30px;
  padding: 0 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: 8px;
  flex-shrink: 0;
}

.logo-icon {
  font-size: 1.2rem;
}

.logo-text {
  font-weight: 700;
  font-size: 1.05rem;
  color: #1677FF;
  white-space: nowrap;
}

.cart-badge {
  margin-left: 4px;
}

.float-toolbar {
  position: fixed;
  top: 52px;
  right: 8px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.theme-float-wrap {
  position: fixed;
  top: 16px;
  right: 8px;
  z-index: 1000;
}

.theme-float-btn {
  font-size: 1.1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.user-float-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.user-float-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677FF, #4096ff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.user-float-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1f2a3e;
  white-space: nowrap;
}

.logout-float-btn {
  width: 100%;
  border-radius: 20px;
  margin-top: 2px;
}

html.dark .user-float-name {
  color: #e0e0e0;
}

@media (max-width: 800px) {
  .app-navbar {
    flex-wrap: wrap;
    justify-content: center;
    padding: 8px 12px;
  }

  .logo-area {
    margin-right: 0;
  }
}
</style>
