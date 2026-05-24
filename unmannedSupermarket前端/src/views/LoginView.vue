<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { loginApi, registerApi, verifyIdentityApi, resetPasswordApi } from '../api/auth'
import { showToast } from '../composables/useToast'
import SliderCaptcha from '../components/SliderCaptcha.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeTab = ref<'login' | 'register'>('login')

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  phone: ''
})

// 忘记密码
const isForgotMode = ref(false)
const forgotStep = ref<'verify' | 'reset'>('verify')
const forgotForm = reactive({
  username: '',
  phone: '',
  newPassword: '',
  confirmPassword: ''
})

const loading = ref(false)

// 验证码
const captchaVerified = ref(false)
const captchaKey = ref(0)

function onCaptchaVerified(_token: string) {
  captchaVerified.value = true
}

function resetCaptcha() {
  captchaVerified.value = false
  captchaKey.value++
}

async function handleLogin() {
  if (!loginForm.username.trim()) {
    showToast('请输入用户名', 'warning')
    return
  }
  if (!loginForm.password) {
    showToast('请输入密码', 'warning')
    return
  }
  if (!captchaVerified.value) {
    showToast('请先完成验证码', 'warning')
    return
  }
  loading.value = true
  try {
    const res = await loginApi({
      username: loginForm.username.trim(),
      password: loginForm.password
    })
    const { token, ...userInfo } = res.data.data
    authStore.setAuth(token, userInfo)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    resetCaptcha()
  }
  finally { loading.value = false }
}

async function handleRegister() {
  if (!registerForm.username.trim()) {
    showToast('请输入用户名', 'warning')
    return
  }
  if (!registerForm.password) {
    showToast('请输入密码', 'warning')
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    showToast('两次密码不一致', 'warning')
    return
  }
  if (!registerForm.phone.trim()) {
    showToast('请输入手机号', 'warning')
    return
  }
  if (!/^1[3-9]\d{9}$/.test(registerForm.phone.trim())) {
    showToast('手机号格式不正确', 'warning')
    return
  }
  if (!captchaVerified.value) {
    showToast('请先完成验证码', 'warning')
    return
  }
  loading.value = true
  try {
    const res = await registerApi({
      username: registerForm.username.trim(),
      password: registerForm.password,
      confirmPassword: registerForm.confirmPassword,
      phone: registerForm.phone.trim()
    })
    const loginRes = await loginApi({
      username: res.data.data.username,
      password: registerForm.password
    })
    const { token, ...userInfo } = loginRes.data.data
    authStore.setAuth(token, userInfo)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    resetCaptcha()
  }
  finally { loading.value = false }
}

function exitForgotMode() {
  isForgotMode.value = false
  forgotStep.value = 'verify'
  forgotForm.username = ''
  forgotForm.phone = ''
  forgotForm.newPassword = ''
  forgotForm.confirmPassword = ''
}

async function handleVerifyIdentity() {
  if (!forgotForm.username.trim()) {
    showToast('请输入用户名', 'warning')
    return
  }
  if (!forgotForm.phone.trim()) {
    showToast('请输入手机号', 'warning')
    return
  }
  if (!/^1[3-9]\d{9}$/.test(forgotForm.phone.trim())) {
    showToast('手机号格式不正确', 'warning')
    return
  }
  loading.value = true
  try {
    await verifyIdentityApi(forgotForm.username.trim(), forgotForm.phone.trim())
    showToast('身份验证通过，请设置新密码', 'success')
    forgotStep.value = 'reset'
  } catch { /* 拦截器已处理 */ }
  finally { loading.value = false }
}

async function handleResetPassword() {
  if (!forgotForm.newPassword) {
    showToast('请输入新密码', 'warning')
    return
  }
  if (forgotForm.newPassword !== forgotForm.confirmPassword) {
    showToast('两次密码不一致', 'warning')
    return
  }
  loading.value = true
  try {
    await resetPasswordApi(forgotForm.username.trim(), forgotForm.phone.trim(), forgotForm.newPassword)
    showToast('密码重置成功，请登录', 'success')
    exitForgotMode()
  } catch { /* 拦截器已处理 */ }
  finally { loading.value = false }
}

</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">👁️‍🗨️</div>
        <h2>眸界·无感智付</h2>
        <p>智慧零售无感支付系统</p>
      </div>

      <div class="auth-bar">
        <div class="auth-tabs">
          <button :class="['tab-btn', { active: activeTab === 'login' }]" @click="activeTab = 'login'">登录</button>
          <button :class="['tab-btn', { active: activeTab === 'register' }]" @click="activeTab = 'register'">注册</button>
        </div>
      </div>

      <div class="auth-content">
        <!-- 登录表单 -->
        <div v-if="activeTab === 'login'" class="form-panel">
          <!-- 忘记密码面板 -->
          <div v-if="isForgotMode" class="form-panel">
            <p class="forgot-hint">{{ forgotStep === 'verify' ? '请输入用户名和手机号进行身份验证' : '请设置新密码' }}</p>
            <!-- 步骤1：验证身份 -->
            <el-form v-if="forgotStep === 'verify'" @submit.prevent="handleVerifyIdentity">
              <el-form-item>
                <el-input v-model="forgotForm.username" placeholder="用户名" size="large" />
              </el-form-item>
              <el-form-item>
                <el-input v-model="forgotForm.phone" placeholder="手机号" size="large" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="large" :loading="loading" native-type="submit" style="width:100%">
                  {{ loading ? '验证中...' : '验证身份' }}
                </el-button>
              </el-form-item>
            </el-form>
            <!-- 步骤2：重置密码 -->
            <el-form v-else @submit.prevent="handleResetPassword">
              <el-form-item>
                <el-input v-model="forgotForm.newPassword" type="password" placeholder="新密码" size="large" show-password />
              </el-form-item>
              <el-form-item>
                <el-input v-model="forgotForm.confirmPassword" type="password" placeholder="确认新密码" size="large" show-password />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="large" :loading="loading" native-type="submit" style="width:100%">
                  {{ loading ? '重置中...' : '重置密码' }}
                </el-button>
              </el-form-item>
            </el-form>
            <p class="forgot-link">
              <a href="#" @click.prevent="exitForgotMode">返回登录</a>
            </p>
          </div>

          <!-- 正常登录 -->
          <el-form v-else @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-form-item>
              <SliderCaptcha :key="captchaKey" @verified="onCaptchaVerified" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="!captchaVerified" native-type="submit" style="width:100%">
                {{ loading ? '登录中...' : '登录系统' }}
              </el-button>
            </el-form-item>
          </el-form>

          <p v-if="!isForgotMode" class="forgot-link">
            <a href="#" @click.prevent="isForgotMode = true">忘记密码？</a>
          </p>
        </div>

        <!-- 注册表单 -->
        <div v-if="activeTab === 'register'" class="form-panel">
          <el-form @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="registerForm.username" placeholder="用户名" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.phone" placeholder="手机号" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" size="large" show-password />
            </el-form-item>
            <el-form-item>
              <SliderCaptcha :key="captchaKey" @verified="onCaptchaVerified" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" :loading="loading" :disabled="!captchaVerified" native-type="submit" style="width:100%">
                {{ loading ? '注册中...' : '注册并登录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>

      </div>

      <p class="login-footer">无感支付 · 智能零售 · 绿色能效</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #EFF4FF 0%, #FFFFFF 100%);
}

.login-card {
  width: 460px;
  max-width: 92%;
  background: #fff;
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.login-header { text-align: center; margin-bottom: 20px; }
.login-logo { font-size: 3rem; }
.login-header h2 { color: #1677FF; margin: 8px 0 4px; }
.login-header p { color: gray; font-size: 0.9rem; }

.auth-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  border-bottom: 2px solid #ebeef5;
  margin-bottom: 20px;
}

.auth-tabs { display: flex; gap: 4px; }

.tab-btn {
  background: none;
  border: none;
  padding: 10px 20px;
  font-size: 0.95rem;
  color: #909399;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.2s, border-color 0.2s;
}

.tab-btn:hover { color: #1677FF; }
.tab-btn.active { color: #1677FF; border-bottom-color: #1677FF; font-weight: 600; }

.auth-content { min-height: 240px; }

.form-panel { animation: fadeIn 0.2s; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.forgot-link { text-align: center; margin-top: 12px; font-size: 0.85rem; }
.forgot-link a { color: #1677FF; text-decoration: none; }
.forgot-link a:hover { text-decoration: underline; }

.forgot-hint { text-align: center; color: #909399; font-size: 0.85rem; margin-bottom: 12px; }

.login-footer { text-align: center; margin-top: 20px; font-size: 12px; color: #aaa; }
</style>
