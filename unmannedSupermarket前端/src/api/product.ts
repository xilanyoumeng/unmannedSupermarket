import request from './request'
import type { ApiResponse, PageData, Product, RecognizeResponse, HotProduct } from '../types'

// ===== 商品分页 =====
export function getProductsApi(params: {
  page?: number
  pageSize?: number
  keyword?: string
  category?: string
} = {}) {
  return request.get<ApiResponse<PageData<Product>>>('/product/page', { params })
}

// ===== 已上架商品（智慧购物展示用） =====
export function getListedProductsApi(params: {
  page?: number
  pageSize?: number
  keyword?: string
  category?: string
} = {}) {
  return request.get<ApiResponse<PageData<Product>>>('/product/listed', { params })
}

// ===== 商品详情 =====
export function getProductApi(id: number) {
  return request.get<ApiResponse<Product>>(`/product/detail/${id}`)
}

// ===== 新增商品 =====
export function createProductApi(data: Partial<Product>) {
  return request.post<ApiResponse<Product>>('/product/add', data)
}

// ===== 修改商品 =====
export function updateProductApi(id: number, data: Partial<Product>) {
  return request.put<ApiResponse<Product>>(`/product/update/${id}`, data)
}

// ===== 上架/下架 =====
export function updateProductStatusApi(id: number, status: number) {
  return request.put<ApiResponse<null>>(`/product/status/${id}`, null, { params: { status } })
}

// ===== 删除商品 =====
export function deleteProductApi(id: number) {
  return request.delete<ApiResponse<null>>(`/product/delete/${id}`)
}

// ===== 分类列表 =====
export function getCategoriesApi() {
  return request.get<ApiResponse<string[]>>('/product/categories')
}

// ===== 热销商品（后端暂未实现） =====
export function getHotProductsApi() {
  return request.get<ApiResponse<HotProduct[]>>('/product/hot')
}

// ===== AI商品识别（后端暂未实现） =====
export function recognizeProductApi(formData: FormData) {
  return request.post<ApiResponse<RecognizeResponse>>('/product/recognize', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
