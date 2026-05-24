import request from './request'
import type { ApiResponse, PageData, Order, PayResponse, CreateOrderRequest } from '../types'

export function createOrderApi(data: CreateOrderRequest) {
  return request.post<ApiResponse<Order>>('/orders', data)
}

export function getOrdersApi(params: {
  page?: number
  pageSize?: number
  status?: string
} = {}) {
  return request.get<ApiResponse<PageData<Order>>>('/orders/page', { params })
}

export function getAllOrdersApi(params: {
  page?: number
  pageSize?: number
  status?: string
} = {}) {
  return request.get<ApiResponse<PageData<Order>>>('/orders/all', { params })
}

export function getOrdersByStatusApi(status: string, params: {
  page?: number
  pageSize?: number
} = {}) {
  return request.get<ApiResponse<PageData<Order>>>('/orders/status', {
    params: { status, ...params }
  })
}

export function getOrderApi(id: number) {
  return request.get<ApiResponse<Order>>(`/orders/${id}`)
}

export function payOrderApi(id: number) {
  return request.post<ApiResponse<PayResponse>>(`/orders/${id}/pay`)
}

export function cancelOrderApi(id: number) {
  return request.post<ApiResponse<null>>(`/orders/${id}/cancel`)
}
