import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '../types'
import { setToken, removeToken, getToken } from '../api/auth'
import { getUserInfoApi, updateElderlyModeApi, updateUserInfoApi, type UpdateUserForm } from '../api/user'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(getToken())
  const elderMode = ref(localStorage.getItem('elderMode') === 'true')

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const username = computed(() => user.value?.username ?? '')
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.role === 'super_admin')
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  function normalizeElderMode(value: UserInfo['elderlyMode']) {
    return value === true || value === 1
  }

  function normalizeUser(userInfo: UserInfo): UserInfo {
    return {
      ...userInfo,
      elderlyMode: normalizeElderMode(userInfo.elderlyMode)
    }
  }

  function applyElderMode(enabled: boolean) {
    elderMode.value = enabled
    localStorage.setItem('elderMode', String(enabled))
    document.body.classList.toggle('elder-mode', enabled)
  }

  function setAuth(authToken: string, userInfo: UserInfo) {
    token.value = authToken
    const normalizedUser = normalizeUser(userInfo)
    user.value = normalizedUser
    setToken(authToken)
    applyElderMode(normalizeElderMode(normalizedUser.elderlyMode))
  }

  async function fetchUserProfile() {
    if (!token.value) return
    try {
      const res = await getUserInfoApi()
      const normalizedUser = normalizeUser(res.data.data)
      user.value = normalizedUser
      applyElderMode(normalizeElderMode(normalizedUser.elderlyMode))
    } catch {
      clearAuth()
    }
  }

  async function updateProfile(data: UpdateUserForm) {
    const res = await updateUserInfoApi(data)
    user.value = normalizeUser(res.data.data)
  }

  function clearAuth() {
    token.value = null
    user.value = null
    removeToken()
  }

  async function toggleElderMode() {
    elderMode.value = !elderMode.value
    applyElderMode(elderMode.value)
    try {
      await updateElderlyModeApi(elderMode.value)
    } catch {
      // 本地状态已更新，后端同步失败不回滚
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    username,
    isAdmin,
    isSuperAdmin,
    elderMode,
    setAuth,
    fetchUserProfile,
    updateProfile,
    clearAuth,
    toggleElderMode
  }
})
