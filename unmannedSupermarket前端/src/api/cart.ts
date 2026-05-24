import request from './request'
import type { ApiResponse, PageData, Cart, CartItem, AddCartRequest, UpdateCartItemRequest } from '../types'

// ===== 购物车 =====

// 分页查询当前用户购物车列表
export function getCartPageApi(params: { page?: number; pageSize?: number } = {}) {
  return request.get<ApiResponse<PageData<Cart>>>('/cart/page', { params })
}

// 购物车详情（含明细+商品信息）
export function getCartDetailApi(id: number) {
  return request.get<ApiResponse<Cart>>(`/cart/detail/${id}`)
}

// 创建购物车
export function createCartApi(data: { name: string }) {
  return request.post<ApiResponse<Cart>>('/cart/add', data)
}

// 修改购物车名称
export function updateCartApi(id: number, data: { name: string }) {
  return request.put<ApiResponse<Cart>>(`/cart/update/${id}`, data)
}

// 删除购物车（级联删除明细）
export function deleteCartApi(id: number) {
  return request.delete<ApiResponse<null>>(`/cart/delete/${id}`)
}

// ===== 购物车明细 =====

// 添加商品到购物车（重复则累加数量）
export function addCartItemApi(data: AddCartRequest) {
  return request.post<ApiResponse<CartItem>>('/cart-item/add', data)
}

// 批量修改购物车明细
export function updateCartItemApi(data: UpdateCartItemRequest) {
  return request.put<ApiResponse<null>>('/cart-item/update', data)
}

// 删除明细
export function deleteCartItemApi(id: number) {
  return request.delete<ApiResponse<null>>(`/cart-item/delete/${id}`)
}
