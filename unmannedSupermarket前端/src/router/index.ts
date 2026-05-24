import { createRouter, createWebHashHistory } from 'vue-router'
import { getToken } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录' }
    },
    {
      path: '/',
      name: 'Home',
      component: () => import('../views/HomeView.vue'),
      meta: { title: '首页', requiresAuth: true }
    },

    {
      path: '/shopping',
      name: 'Shopping',
      component: () => import('../views/ShoppingView.vue'),
      meta: { title: '智慧购物', requiresAuth: true }
    },
    {
      path: '/cart',
      name: 'Cart',
      component: () => import('../views/CartView.vue'),
      meta: { title: '购物车', requiresAuth: true }
    },
    {
      path: '/products',
      redirect: '/shopping'
    },
    {
      path: '/orders/:id?',
      redirect: (to) => {
        const id = Array.isArray(to.params.id) ? to.params.id[0] : to.params.id
        return id
          ? { name: 'OrderConfirm', params: { id }, query: to.query }
          : { name: 'Profile' }
      }
    },
    {
      path: '/order/:id?',
      redirect: (to) => {
        const id = Array.isArray(to.params.id) ? to.params.id[0] : to.params.id
        return id
          ? { name: 'OrderConfirm', params: { id }, query: to.query }
          : { name: 'Profile' }
      }
    },
    {
      path: '/order-confirm/:id',
      name: 'OrderConfirm',
      component: () => import('../views/OrderConfirmView.vue'),
      meta: { title: '订单确认', requiresAuth: true }
    },
    {
      path: '/payment-success',
      name: 'PaymentSuccess',
      component: () => import('../views/PaymentSuccessView.vue'),
      meta: { title: '支付成功', requiresAuth: true }
    },
    {
      path: '/assistant',
      name: 'Assistant',
      component: () => import('../views/AIAssistantView.vue'),
      meta: { title: 'AI导购助手', requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { title: '个人中心', requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../views/AdminView.vue'),
      meta: { title: '后台管理', requiresAuth: true, requireAdmin: true }
    }
  ]
})

// 路由守卫 —— JWT鉴权 + 角色权限
router.beforeEach(async (to, _from, next) => {
  document.title = (to.meta.title as string) || '眸界·无感智付'

  const token = getToken()
  const authStore = useAuthStore()

  if (to.meta.requiresAuth) {
    if (!token) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    if (!authStore.user) {
      await authStore.fetchUserProfile()
    }
    if (!authStore.user) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 已登录用户访问登录页，直接进首页
  if (to.name === 'Login' && token) {
    if (!authStore.user) {
      await authStore.fetchUserProfile()
    }
    if (authStore.user) {
      next({ name: 'Home' })
      return
    }
  }

  // 管理员权限校验
  if (to.meta.requireAdmin) {
    // 如果用户信息未加载，先拉取
    if (!authStore.user) {
      await authStore.fetchUserProfile()
    }
    if (!authStore.isAdmin) {
      next({ name: 'Home' })
      return
    }
  }

  next()
})

export default router
