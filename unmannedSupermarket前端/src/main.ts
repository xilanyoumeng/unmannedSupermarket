import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setRouter } from './utils/status'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './style.css'

// 初始化主题
const savedTheme = localStorage.getItem('theme')
if (savedTheme === 'dark') {
  document.documentElement.classList.add('dark')
}

// 初始化适老化模式
if (localStorage.getItem('elderMode') === 'true') {
  document.body.classList.add('elder-mode')
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
setRouter(router)

app.mount('#app')
