import request from './request'
import type { ApiResponse } from '../types'

export function uploadImageApi(formData: FormData) {
  return request.post<ApiResponse<{ url: string }>>('/file/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
