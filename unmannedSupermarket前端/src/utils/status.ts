import type { Router } from 'vue-router'
import { TOKEN_KEY } from '../api/request'
import { showToast } from '../composables/useToast'

let router: Router | null = null

export function setRouter(r: Router) {
  router = r
}

export function handleUnauthorized(message = '登录已过期，请重新登录') {
  sessionStorage.removeItem(TOKEN_KEY)
  showToast(message, 'warning')
  if (router) {
    router.push('/login')
  } else {
    window.location.hash = '#/login'
  }
}
