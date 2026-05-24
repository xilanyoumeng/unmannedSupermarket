import request from './request'
import type {
  ApiResponse,
  UserInfo,
  PageData,
  UserAiModelConfig,
  UserAiModelConfigForm,
  UserMultimodalModelConfig,
  UserMultimodalModelConfigForm
} from '../types'

export function getUserInfoApi() {
  return request.get<ApiResponse<UserInfo>>('/user/info')
}

export interface UpdateUserForm {
  nickname?: string
  email?: string
  phone?: string
}

export function updateUserInfoApi(data: UpdateUserForm) {
  return request.put<ApiResponse<UserInfo>>('/user/info', data)
}

export function updateElderlyModeApi(elderlyMode: boolean) {
  return request.put<ApiResponse<null>>('/user/elderly-mode', { elderlyMode })
}

export function getUserAiModelConfigApi() {
  return request.get<ApiResponse<UserAiModelConfig | null>>('/user/ai-model')
}

export function saveUserAiModelConfigApi(data: UserAiModelConfigForm) {
  return request.put<ApiResponse<UserAiModelConfig>>('/user/ai-model', data)
}

export function deleteUserAiModelConfigApi() {
  return request.delete<ApiResponse<null>>('/user/ai-model')
}

export function getUserMultimodalModelConfigApi() {
  return request.get<ApiResponse<UserMultimodalModelConfig | null>>('/user/multimodal-model')
}

export function saveUserMultimodalModelConfigApi(data: UserMultimodalModelConfigForm) {
  return request.put<ApiResponse<UserMultimodalModelConfig>>('/user/multimodal-model', data)
}

export function deleteUserMultimodalModelConfigApi() {
  return request.delete<ApiResponse<null>>('/user/multimodal-model')
}

export function getUserPageApi(page = 1, pageSize = 20) {
  return request.get<ApiResponse<PageData<UserInfo>>>('/user/page', {
    params: { page, pageSize }
  })
}

export function updateUserRoleApi(userId: number, role: string) {
  return request.put<ApiResponse<null>>(`/user/${userId}/role`, { role })
}

export function deleteUserApi(userId: number) {
  return request.delete<ApiResponse<null>>(`/user/${userId}`)
}

export function adminResetPasswordApi(userId: number) {
  return request.put<ApiResponse<null>>(`/user/${userId}/reset-password`)
}
