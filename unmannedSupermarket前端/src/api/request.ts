import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse } from '../types'
import { handleUnauthorized } from '../utils/status'
import { showToast } from '../composables/useToast'

const TOKEN_KEY = 'mz_token'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 —— 附加JWT令牌
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = sessionStorage.getItem(TOKEN_KEY)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// 响应拦截器 —— 统一状态码处理
request.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    // 后端返回的业务状态码非200时也视为逻辑错误
    if (body.code !== 200) {
      handleBusinessCode(body.code, body.message, isAiServiceRequest(response.config))
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      const { status, data } = error.response
      const msg = (data as ApiResponse)?.message || ''
      handleHttpStatus(status, msg, isAiServiceRequest(error.config))
    } else if (error.code === 'ECONNABORTED') {
      showToast('请求超时，请检查网络后重试', 'error')
    } else {
      showToast('网络异常，无法连接服务器', 'error')
    }
    return Promise.reject(error)
  }
)

function isAiServiceRequest(config?: { url?: string }): boolean {
  const url = config?.url || ''
  return (
    url.startsWith('/session') ||
    url.startsWith('/product/recognize') ||
    url.startsWith('/product/vector-status') ||
    url.startsWith('/chat')
  )
}

// HTTP状态码处理
function handleHttpStatus(status: number, message: string, aiServiceRequest = false) {
  switch (status) {
    case 400:
      showToast(message || '请求参数有误', 'warning')
      break
    case 401:
      if (aiServiceRequest) {
        showToast(message || 'AI服务缺少登录用户信息，请刷新后重试', 'warning')
      } else {
        handleUnauthorized(message)
      }
      break
    case 403:
      if (aiServiceRequest) {
        showToast(message || 'AI服务权限不足，无法执行该操作', 'error')
      } else {
        showToast('权限不足，无法执行该操作', 'error')
      }
      break
    case 404:
      showToast(message || '请求的资源不存在', 'error')
      break
    case 405:
      showToast(message || '请求方法不允许', 'error')
      break
    case 409:
      showToast(message || '数据冲突，请刷新后重试', 'warning')
      break
    case 500:
      showToast('服务器内部错误，请稍后重试', 'error')
      break
    default:
      showToast(message || `请求异常 (${status})`, 'error')
  }
}

// 业务状态码处理
function handleBusinessCode(code: number, message: string, aiServiceRequest = false) {
  switch (code) {
    case 401:
    case 403:
      if (aiServiceRequest) {
        showToast(message || 'AI服务暂时无法获取当前用户信息', 'warning')
      } else {
        handleUnauthorized(message)
      }
      break
    default:
      showToast(message || `操作失败 (${code})`, 'error')
  }
}

export { TOKEN_KEY }
export default request
