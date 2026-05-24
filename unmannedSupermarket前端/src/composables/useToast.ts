import { ElMessage, ElMessageBox } from 'element-plus'

export function showToast(
  message: string,
  type: 'success' | 'error' | 'warning' | 'info' = 'info',
  duration = 3000
) {
  ElMessage({ message, type, duration })
}

export function showConfirm(message: string, title = '确认操作'): Promise<boolean> {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => true)
    .catch(() => false)
}

export function useToast() {
  return {
    toasts: [],
    showToast,
    removeToast: () => {},
    confirmState: { visible: false, message: '', title: '', resolve: null as ((v: boolean) => void) | null },
    showConfirm,
    resolveConfirm: () => {}
  }
}
