import request, { TOKEN_KEY } from './request'
import type { ApiResponse, LoginRequest, RegisterRequest, AuthResponse, UserInfo } from '../types'

export function loginApi(data: LoginRequest) {
  return request.post<ApiResponse<AuthResponse>>('/user/login', data)
}

export function registerApi(data: RegisterRequest) {
  return request.post<ApiResponse<UserInfo>>('/user/register', data)
}

export function verifyIdentityApi(username: string, phone: string) {
  return request.post<ApiResponse<null>>('/user/verify-identity', { username, phone })
}

export function resetPasswordApi(username: string, phone: string, newPassword: string) {
  return request.post<ApiResponse<null>>('/user/reset-password', { username, phone, newPassword })
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}
