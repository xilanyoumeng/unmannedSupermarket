# 眸界·无感智付 — 智慧零售无感支付系统

多模态生物识别 + 毫秒级无感结算的无人超市前端系统。基于 Vue 3 + TypeScript + Vite 构建，采用 Element Plus 组件库，JWT 令牌进行身份鉴权，所有业务数据通过后端 API 获取。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3.5 (Composition API + `<script setup>`) |
| 语言 | TypeScript 6.0 |
| 构建 | Vite 5.4 |
| UI 组件库 | Element Plus |
| 路由 | Vue Router 4.6 (Hash 模式) |
| 状态管理 | Pinia 3.0 |
| HTTP 请求 | Axios 1.16 (拦截器统一处理 JWT 与状态码) |
| 样式 | Element Plus + 原生 CSS (CSS 变量 + 适老化响应式) |

## 项目结构

```
src/
├── api/                    # API 请求层
│   ├── request.ts          # Axios 实例 · 拦截器 · 超时 15s · 状态码统一处理
│   ├── auth.ts             # 登录 / 注册 / 登出 / 令牌存取
│   ├── product.ts          # 商品列表 / 详情 + AI 图像识别 (购物端)
│   ├── cart.ts             # 购物车增删改查
│   ├── order.ts            # 订单创建 / 支付 / 取消
│   ├── upload.ts           # 通用图片上传
│   ├── user.ts             # 用户资料 / 适老模式切换
│   └── admin.ts            # 管理端统计 / 用户分页 / 商品 CRUD / 订单管理 (分页+搜索)
├── assets/                 # 静态资源 (图片、图标等)
├── components/             # 公共组件
├── composables/
│   └── useToast.ts         # 全局通知 (ElMessage) / 确认对话框 (ElMessageBox) 封装
├── types/index.ts          # 全部 TypeScript 接口定义
├── router/index.ts         # 路由表 + beforeEach 鉴权守卫
├── stores/
│   ├── auth.ts             # 认证状态 (token / user / elderMode)
│   └── cart.ts             # 购物车状态 (items / totalCount / totalPrice)
├── utils/status.ts         # 鉴权失效工具 (清除 token + 路由跳转)
├── views/                  # 页面视图
│   ├── LoginView.vue       # 登录/注册双 Tab 表单 (el-tabs + el-form)
│   ├── HomeView.vue        # 首页功能入口卡片 (el-card)
│   ├── ShoppingView.vue    # 商品列表 + AI 商品识别 + 加入购物车 (el-card + el-upload)
│   ├── CartView.vue        # 购物车表格 → 创建订单 → 无感支付 (el-table + el-input-number)
│   ├── PaymentSuccessView.vue  # 支付结果展示 (el-result + el-descriptions)
│   ├── ProfileView.vue     # 个人档案 · 交易记录 · 适老化开关 (el-descriptions + el-switch)
│   └── AdminView.vue       # 商品管理 · 用户管理 · 订单管理 · 交易统计 (el-menu + el-table + el-pagination)
├── App.vue                 # 根布局 (el-menu 导航栏 + router-view)
├── main.ts                 # 入口 (注册 Pinia + Router + ElementPlus + setRouter)
└── style.css               # 全局样式 · CSS 变量 · 适老化模式 (含 Element Plus 变量覆盖)
```

Vite 配置了路径别名 `@` → `src/`，所有模块导入可使用 `@/` 前缀。

## 功能页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录/注册 | `/login` | 双 Tab 切换表单 (el-tabs)，登录/注册成功存储 JWT 并跳转（支持 redirect 回跳） |
| 首页 | `/` | 功能卡片导航 (el-card)，需登录 |
| 智慧购物 | `/shopping` | 商品卡片列表 + AI 商品图像识别 + 加入购物车 |
| 购物车 | `/cart` | el-table 展示 + el-input-number 调数量 + el-popconfirm 删除 / 一键结算 → 无感支付 |
| 支付成功 | `/payment-success` | el-result 成功图标 + el-descriptions 展示订单号、金额、支付时间 |
| 个人中心 | `/profile` | el-descriptions 用户信息 + el-table 交易记录 + el-switch 适老化开关 |
| 后台管理 | `/admin` | 侧栏 el-menu 四 Tab：商品管理 (分页+CRUD) · 用户管理 (分页) · 订单管理 (分页+状态筛选) · 交易统计 |

### 页面入口守卫

- **智慧购物** (`/shopping`) 和 **购物车** (`/cart`) 需要登录后才能访问。

### 后台管理

AdminView 采用左侧 `el-menu` 导航 + 右侧内容区布局，包含四个功能模块：

| 模块 | 功能 | 分页 |
|------|------|------|
| 商品管理 | 商品列表 (el-table)、新增/编辑弹窗 (el-dialog + el-form)、删除确认 (ElMessageBox) | 10 条/页 |
| 用户管理 | 用户列表，适老模式标签 | 10 条/页 |
| 订单管理 | 订单列表，el-select 状态筛选 (全部/待支付/已支付/已取消)，el-tag 状态标签 | 10 条/页 |
| 交易统计 | 总交易笔数、总金额、用户数、商品数卡片展示 | — |

## JWT 鉴权流程

```
1. 用户提交登录/注册表单
2. 后端验证返回 { token, user }
3. 前端将 token 存入 sessionStorage (key: mz_token)
4. Axios 请求拦截器自动为每个请求附加 Authorization: Bearer <token>
5. 响应拦截器捕获 HTTP 401/403 或业务码 401/403 → 清除 token → ElMessage 提示 → 跳转 /login
6. 路由守卫 beforeEach: 无 token 访问需授权页面时重定向到 /login?redirect=<原路径>
7. 已登录用户访问 /login 自动重定向到 /
8. 登录成功后优先跳转 redirect 参数指向的原始路径
```

## UI 通知系统

全局通知和确认对话框通过 [src/composables/useToast.ts](src/composables/useToast.ts) 统一封装，底层调用 Element Plus 的 `ElMessage` 和 `ElMessageBox`：

```typescript
import { showToast, showConfirm } from '../composables/useToast'

// 通知提示 (success / error / warning / info)
showToast('操作成功', 'success')

// 确认对话框，返回 Promise<boolean>
const confirmed = await showConfirm('确定要删除吗？', '删除确认')
```

- `showToast()` — 所有表单校验、操作成功/失败、网络错误等 30+ 调用点统一使用
- `showConfirm()` — 删除确认等需要用户二次确认的场景

## 后端接口约定

后端服务运行在 `localhost:8065`，前端开发服务器通过 Vite proxy 将 `/api` 转发至后端。Axios 实例超时设置为 15 秒。

所有接口统一返回格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 认证模块

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/api/auth/login` | `{ username, password }` | 登录，返回 `{ token, user }` |
| POST | `/api/auth/register` | `{ username, password, confirmPassword, payAccount }` | 注册，返回 `{ token, user }` |
| POST | `/api/auth/logout` | — | 登出 |

### 商品模块 (购物端)

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/products` | — | 商品列表 |
| GET | `/api/products/:id` | — | 商品详情 |
| POST | `/api/products/recognize` | `FormData { image }` | AI 商品识别 (Content-Type: multipart/form-data)，返回 `{ name, price, confidence, productId? }` |

> 商品的新增、修改、删除操作统一由管理端接口 `/api/admin/products` 提供，见下方管理端章节。

### 购物车模块

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/cart` | — | 获取购物车列表 |
| POST | `/api/cart` | `{ productId, quantity }` | 添加商品 (成功后重新拉取全量购物车) |
| PUT | `/api/cart/:id` | `{ quantity }` | 修改数量 |
| DELETE | `/api/cart/:id` | — | 删除单项 |
| DELETE | `/api/cart` | — | 清空购物车 |

### 订单模块 (购物端)

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/orders` | — | 订单列表 |
| GET | `/api/orders/:id` | — | 订单详情 |
| POST | `/api/orders` | `{ cartItemIds? }` | 创建订单 |
| POST | `/api/orders/:id/pay` | — | 支付，返回 `{ orderNo, amount, paidAt }` |
| PUT | `/api/orders/:id/cancel` | — | 取消订单 |

### 用户模块

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| GET | `/api/user/profile` | — | 获取用户信息 |
| PUT | `/api/user/profile` | 部分字段 | 更新用户信息 |
| PUT | `/api/user/elder-mode` | `{ enabled }` | 切换适老模式 (同步更新 body CSS class) |

### 管理端 — 统计与用户

| 方法 | 路径 | 参数 | 说明 |
|------|------|------|------|
| GET | `/api/admin/stats` | — | 统计数据 `{ totalOrders, totalAmount, totalUsers, totalProducts }` |
| GET | `/api/admin/users` | `?page=&pageSize=` | 用户分页列表 → `PageData<AdminUser>` |

### 管理端 — 商品管理

| 方法 | 路径 | 请求体/参数 | 说明 |
|------|------|--------|------|
| GET | `/api/admin/products` | `?page=&pageSize=&keyword=&category=` | 商品分页列表（支持搜索和分类筛选）→ `PageData<Product>` |
| GET | `/api/admin/products/:id` | — | 商品详情 |
| POST | `/api/admin/products` | `{ name, price, stock, category?, description? }` | 新增商品 |
| PUT | `/api/admin/products/:id` | 部分字段 | 修改商品（部分字段更新） |
| DELETE | `/api/admin/products/:id` | — | 删除商品 |

### 管理端 — 订单管理

| 方法 | 路径 | 请求体/参数 | 说明 |
|------|------|--------|------|
| GET | `/api/admin/orders` | `?page=&pageSize=&status=` | 订单分页列表（支持状态筛选 pending/paid/cancelled）→ `PageData<Order>` |
| GET | `/api/admin/orders/:id` | — | 订单详情 |
| PUT | `/api/admin/orders/:id/cancel` | — | 取消订单 |

### 上传模块

| 方法 | 路径 | 请求体 | 说明 |
|------|------|--------|------|
| POST | `/api/upload/image` | `FormData` | 通用图片上传 (Content-Type: multipart/form-data)，返回 `{ url }` |

## 状态码处理

| HTTP 状态码 | 前端行为 |
|-------------|----------|
| 400 | `showToast` 提示参数错误 (warning) |
| 401 | `handleUnauthorized()` → 清除 `sessionStorage` 中 token → `showToast` 提示 → 跳转 `/login` |
| 403 | `showToast` 提示权限不足 (error) |
| 404 | `showToast` 提示资源不存在 (error) |
| 409 | `showToast` 提示数据冲突 (warning) |
| 500 | `showToast` 提示服务器错误 (error) |
| 超时 (`ECONNABORTED`) | `showToast` 提示请求超时 (error) |
| 网络异常 | `showToast` 提示无法连接服务器 (error) |
| 业务码 401/403 | 同 HTTP 401 处理 |
| 业务码 非200 | `showToast` 显示后端返回的 message (error) |

## 适老化模式

`ProfileView.vue` 提供 `el-switch` 适老化开关，调用 `/api/user/elder-mode` 接口同步状态。开启后通过 `document.body.classList.add('elder-mode')` 激活全局样式覆盖：

- 基础字号从 16px 放大至 20.8px（+30%）
- 主色调调整为更高对比度的 `#005fcc`
- 背景与文字对比度增强
- 边框加粗、阴影加深
- Element Plus 组件同步跟随 (`--el-font-size-base`, `--el-color-primary`, `--el-border-color`)

CSS 变量定义和适老化覆盖均在 [style.css](src/style.css) 中维护。

## 鉴权失效处理

`src/utils/status.ts` 导出 `setRouter()` 和 `handleUnauthorized()` 两个工具函数：

- **setRouter(router)**: 在 `main.ts` 中调用，将路由实例注入工具模块，避免循环依赖。
- **handleUnauthorized(message)**: 清除 `sessionStorage` 中的 token，通过 `showToast` 提示用户，并通过注入的 router 实例或降级 `window.location.hash` 跳转到 `/login`。

响应拦截器中 HTTP 401/403 和业务码 401/403 均调用 `handleUnauthorized()` 统一处理。

## 本地运行

```bash
# 安装依赖
npm install

# 启动开发服务器 (默认 http://localhost:5173)
npm run dev

# 类型检查 + 生产构建
npm run build

# 预览生产构建
npm run preview
```

开发模式下，所有 `/api` 请求自动代理到 `http://localhost:8065`（配置在 [vite.config.ts](vite.config.ts)）。

后端服务需在 8065 端口运行，并按上述接口约定提供对应 API。
