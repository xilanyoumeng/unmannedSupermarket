import request from './request'
import type { ApiResponse } from '../types'

// ========== 会话相关类型 ==========
export interface SessionInfo {
  session_id: string
  title: string
  created_at: string
  updated_at?: string
  last_message?: string
  is_existing?: boolean
}

export interface SessionMessage {
  role: string
  content: string
  time?: string
  action?: {
    type: string
    label: string
    payload?: unknown
  }
}

// ========== 创建会话 ==========
export function createSessionApi(data: { user_id?: number; username?: string }) {
  return request.post<ApiResponse<SessionInfo>>('/session/create', data)
}

// ========== 查询所有会话 ==========
export function listSessionsApi(params: { user_id?: number } = {}) {
  return request.get<ApiResponse<{ sessions: SessionInfo[] }>>('/session/list', { params })
}

// ========== 加载会话消息 ==========
export function loadSessionApi(sessionId: string, params: { user_id?: number } = {}) {
  return request.get<ApiResponse<{ messages: SessionMessage[]; missing?: boolean }>>(`/session/${sessionId}/messages`, { params })
}

// ========== 删除会话 ==========
export function deleteSessionApi(sessionId: string, params: { user_id?: number } = {}) {
  return request.delete<ApiResponse<null>>(`/session/${sessionId}`, { params })
}
