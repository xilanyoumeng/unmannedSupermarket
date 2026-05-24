// 通用API响应包装
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

// 分页数据
export interface PageData<T> {
  records: T[]
  total: number
  page: number
  pageSize: number
}

// 用户信息
export interface UserInfo {
  id: number
  username: string
  nickname?: string
  email?: string
  phone?: string
  role?: string
  status?: number
  elderlyMode?: boolean | number
  createTime?: string
  updateTime?: string
}

export interface UserAiModelConfig {
  id?: number
  provider: string
  baseUrl: string
  model: string
  apiKeyMasked?: string
  temperature: number
  maxTokens: number
  topP: number
  enabled: boolean
  updateTime?: string
}

export interface UserAiModelConfigForm {
  provider: string
  baseUrl: string
  model: string
  apiKey?: string
  temperature: number
  maxTokens: number
  topP: number
  enabled: boolean
}

export interface UserMultimodalModelConfig {
  id?: number
  provider: 'dashscope'
  apiKeyMasked?: string
  enabled: boolean
  updateTime?: string
}

export interface UserMultimodalModelConfigForm {
  apiKey?: string
  enabled: boolean
}

// 登录请求
export interface LoginRequest {
  username: string
  password: string
}

// 注册请求
export interface RegisterRequest {
  username: string
  password: string
  confirmPassword: string
  phone: string
}

// 登录响应（Java 后端返回 token 和用户字段在同一层）
export interface AuthResponse extends UserInfo {
  token: string
}

// 商品
export interface Product {
  id: number
  name: string
  price: number
  stock: number
  category: string
  description: string
  image: string
  barcode: string
  status: number
  createTime: string
  updateTime: string
}

// 商品表单 (新增/修改)
export interface ProductForm {
  name: string
  price: number
  stock: number
  category: string
  description: string
  image: string
  barcode: string
}

// 购物车（含商品明细）
export interface Cart {
  id: number
  name: string
  userId: number
  createTime: string
  items: CartItem[]
}

// 购物车项
export interface CartItem {
  id: number
  cartId: number
  productId: number
  productName: string
  productImage?: string
  productPrice: number
  quantity: number
  createTime: string
}

// 添加购物车商品请求
export interface AddCartRequest {
  productId: number
  quantity: number
}

// 批量更新购物车明细请求
export interface UpdateCartItemRequest {
  cartId: number
  items: CartItemUpdateItem[]
}

export interface CartItemUpdateItem {
  productId: number
  quantity: number
}

// 订单
export interface Order {
  id: number
  orderNo: string
  amount: number
  itemsCount: number
  status: OrderStatus
  username?: string
  items?: OrderItem[]
  createdAt: string
  paidAt?: string
}

// 订单状态
export type OrderStatus = '待支付' | '已支付' | '已取消'

// 订单项
export interface OrderItem {
  productId: number
  productName: string
  price: number
  quantity: number
  subtotal: number
}

// 创建订单请求
export interface CreateOrderRequest {
  items: CreateOrderItemRequest[]
}

export interface CreateOrderItemRequest {
  productId: number
  quantity: number
}

// 支付请求
export interface PayRequest {
  orderId: number
}

// 支付响应
export interface PayResponse {
  orderNo: string
  amount: number
  paidAt: string
}

// 商品分类
export interface Category {
  id: number
  name: string
  icon?: string
  productCount?: number
}

// 热销商品 (后端返回0-3个)
export interface HotProduct {
  id: number
  name: string
  price: number
  stock: number
  category: string
  description: string
  image: string
  barcode: string
  salesCount: number
  hotCount: number
  createTime: string
  updateTime: string
}

// 商品识别请求/响应
export interface RecognizeRequest {
  image: File
}

export interface RecognizeResponse {
  name: string
  price: number
  confidence: number
  productId?: number
}

// 管理员用户列表项
export interface AdminUser {
  id: number
  username: string
  nickname?: string
  phone?: string
  email?: string
  role?: string
  status?: number
  createTime?: string
}
