<script setup lang="ts">
import { ref, onMounted, watch, reactive } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getOrdersApi, getOrderApi, cancelOrderApi } from '../api/order'
import {
  deleteUserAiModelConfigApi,
  deleteUserMultimodalModelConfigApi,
  getUserAiModelConfigApi,
  getUserMultimodalModelConfigApi,
  saveUserAiModelConfigApi,
  saveUserMultimodalModelConfigApi
} from '../api/user'
import { showToast } from '../composables/useToast'
import type { Order, UserAiModelConfigForm, UserMultimodalModelConfigForm } from '../types'

const router = useRouter()
const authStore = useAuthStore()
const orders = ref<Order[]>([])
const loading = ref(false)
const ordersPage = ref(1)
const ordersTotal = ref(0)
const ordersPageSize = 10

const detailVisible = ref(false)
const detailOrder = ref<Order | null>(null)
const detailLoading = ref(false)
const cancelling = ref(false)

// ========== 编辑个人信息 ==========
const editing = ref(false)
const saving = ref(false)
const editForm = reactive({
  nickname: '',
  email: '',
  phone: ''
})

// ========== AI模型配置 ==========
const aiModelLoading = ref(false)
const aiModelSaving = ref(false)
const aiModelDeleting = ref(false)
const aiModelExists = ref(false)
const aiModelApiKeyMasked = ref('')
const aiModelForm = reactive<UserAiModelConfigForm>({
  provider: 'dashscope',
  baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.6-plus',
  apiKey: '',
  temperature: 0.7,
  maxTokens: 2048,
  topP: 0.9,
  enabled: true
})

// ========== 多模态图片识别配置 ==========
const multimodalLoading = ref(false)
const multimodalSaving = ref(false)
const multimodalDeleting = ref(false)
const multimodalExists = ref(false)
const multimodalApiKeyMasked = ref('')
const multimodalForm = reactive<UserMultimodalModelConfigForm>({
  apiKey: '',
  enabled: true
})

onMounted(async () => {
  await Promise.all([loadOrders(), loadAiModelConfig(), loadMultimodalModelConfig()])
})

function startEdit() {
  editForm.nickname = authStore.user?.nickname ?? ''
  editForm.email = authStore.user?.email ?? ''
  editForm.phone = authStore.user?.phone ?? ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function handleSaveProfile() {
  saving.value = true
  try {
    await authStore.updateProfile({
      nickname: editForm.nickname || undefined,
      email: editForm.email || undefined,
      phone: editForm.phone || undefined
    })
    showToast('保存成功', 'success')
    editing.value = false
  } catch {
    // 拦截器已处理
  } finally {
    saving.value = false
  }
}

async function loadAiModelConfig() {
  aiModelLoading.value = true
  try {
    const res = await getUserAiModelConfigApi()
    const config = res.data.data
    aiModelExists.value = !!config
    aiModelApiKeyMasked.value = config?.apiKeyMasked || ''
    aiModelForm.provider = config?.provider || 'dashscope'
    aiModelForm.baseUrl = config?.baseUrl || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    aiModelForm.model = config?.model || 'qwen3.6-plus'
    aiModelForm.apiKey = ''
    aiModelForm.temperature = config?.temperature ?? 0.7
    aiModelForm.maxTokens = config?.maxTokens ?? 2048
    aiModelForm.topP = config?.topP ?? 0.9
    aiModelForm.enabled = config?.enabled ?? true
  } catch {
    aiModelExists.value = false
  } finally {
    aiModelLoading.value = false
  }
}

function applyProviderPreset(provider: string) {
  if (provider === 'dashscope') {
    aiModelForm.baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    if (!aiModelForm.model) aiModelForm.model = 'qwen3.6-plus'
  } else if (provider === 'openai') {
    aiModelForm.baseUrl = 'https://api.openai.com/v1'
  } else if (provider === 'deepseek') {
    aiModelForm.baseUrl = 'https://api.deepseek.com'
    if (!aiModelForm.model) aiModelForm.model = 'deepseek-chat'
  } else if (provider === 'moonshot') {
    aiModelForm.baseUrl = 'https://api.moonshot.cn/v1'
    if (!aiModelForm.model) aiModelForm.model = 'moonshot-v1-8k'
  }
}

async function handleSaveAiModelConfig() {
  if (!aiModelForm.provider.trim()) {
    showToast('请选择或填写模型厂商', 'warning')
    return
  }
  if (!aiModelForm.baseUrl.trim()) {
    showToast('请填写模型服务地址', 'warning')
    return
  }
  if (!aiModelForm.model.trim()) {
    showToast('请填写模型名称', 'warning')
    return
  }
  if (!aiModelExists.value && !aiModelForm.apiKey?.trim()) {
    showToast('首次保存需要填写 API Key', 'warning')
    return
  }

  aiModelSaving.value = true
  try {
    const payload: UserAiModelConfigForm = {
      ...aiModelForm,
      apiKey: aiModelForm.apiKey?.trim() || undefined
    }
    const res = await saveUserAiModelConfigApi(payload)
    const config = res.data.data
    aiModelExists.value = true
    aiModelApiKeyMasked.value = config.apiKeyMasked || ''
    aiModelForm.apiKey = ''
    showToast('AI模型配置已保存', 'success')
  } catch {
    // 拦截器已处理
  } finally {
    aiModelSaving.value = false
  }
}

async function handleDeleteAiModelConfig() {
  try {
    await ElMessageBox.confirm('删除后 AI 导购会回退到系统默认模型配置。确定删除吗？', '删除AI模型配置', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  aiModelDeleting.value = true
  try {
    await deleteUserAiModelConfigApi()
    showToast('AI模型配置已删除', 'success')
    await loadAiModelConfig()
  } catch {
    // 拦截器已处理
  } finally {
    aiModelDeleting.value = false
  }
}

async function loadMultimodalModelConfig() {
  multimodalLoading.value = true
  try {
    const res = await getUserMultimodalModelConfigApi()
    const config = res.data.data
    multimodalExists.value = !!config
    multimodalApiKeyMasked.value = config?.apiKeyMasked || ''
    multimodalForm.apiKey = ''
    multimodalForm.enabled = config?.enabled ?? true
  } catch {
    multimodalExists.value = false
  } finally {
    multimodalLoading.value = false
  }
}

async function handleSaveMultimodalModelConfig() {
  if (!multimodalExists.value && !multimodalForm.apiKey?.trim()) {
    showToast('首次保存需要填写阿里百炼 DashScope API Key', 'warning')
    return
  }

  multimodalSaving.value = true
  try {
    const payload: UserMultimodalModelConfigForm = {
      enabled: multimodalForm.enabled,
      apiKey: multimodalForm.apiKey?.trim() || undefined
    }
    const res = await saveUserMultimodalModelConfigApi(payload)
    const config = res.data.data
    multimodalExists.value = true
    multimodalApiKeyMasked.value = config.apiKeyMasked || ''
    multimodalForm.apiKey = ''
    showToast('图片识别 DashScope Key 已保存', 'success')
  } catch {
    // 拦截器已处理
  } finally {
    multimodalSaving.value = false
  }
}

async function handleDeleteMultimodalModelConfig() {
  try {
    await ElMessageBox.confirm('删除后商品图片识别会回退到系统默认 DashScope Key。确定删除吗？', '删除图片识别配置', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  multimodalDeleting.value = true
  try {
    await deleteUserMultimodalModelConfigApi()
    showToast('图片识别配置已删除', 'success')
    await loadMultimodalModelConfig()
  } catch {
    // 拦截器已处理
  } finally {
    multimodalDeleting.value = false
  }
}

async function loadOrders() {
  loading.value = true
  try {
    const res = await getOrdersApi({
      page: ordersPage.value,
      pageSize: ordersPageSize
    })
    orders.value = res.data.data?.records ?? []
    ordersTotal.value = res.data.data?.total ?? 0
  } catch {
    orders.value = []
  } finally {
    loading.value = false
  }
}

async function handleViewDetail(order: Order) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res = await getOrderApi(order.id)
    detailOrder.value = res.data.data
  } catch {
    detailOrder.value = order
  } finally {
    detailLoading.value = false
  }
}

function handlePay(orderId: number) {
  router.push({ name: 'OrderConfirm', params: { id: orderId } })
}

async function handleCancel(orderId: number) {
  try {
    await ElMessageBox.confirm('确定要取消该订单吗？取消后不可恢复。', '取消订单', {
      confirmButtonText: '确认取消',
      cancelButtonText: '再想想',
      type: 'warning'
    })
  } catch {
    return
  }
  cancelling.value = true
  try {
    await cancelOrderApi(orderId)
    showToast('订单已取消', 'success')
    detailVisible.value = false
    await loadOrders()
  } catch {
    // 拦截器已处理
  } finally {
    cancelling.value = false
  }
}

function handleElderModeChange(_enabled: boolean) {
  authStore.toggleElderMode()
}

watch(ordersPage, () => loadOrders())

function statusTagType(status: string) {
  if (status === '已支付') return 'success'
  if (status === '待支付') return 'warning'
  return 'info'
}

function roleLabel(role?: string) {
  if (role === 'super_admin') return '超级管理员'
  if (role === 'admin') return '管理员'
  if (role === 'user') return '普通用户'
  return role || '—'
}

function avatarLetter(): string {
  const name = authStore.user?.nickname || authStore.user?.username || '?'
  return name.charAt(0).toUpperCase()
}
</script>

<template>
  <div class="profile-page">
    <!-- ===== 个人信息卡片 ===== -->
    <el-card class="profile-card">
      <div class="profile-header">
        <h2>👤 个人档案</h2>
        <el-button v-if="!editing" type="primary" size="small" @click="startEdit">
          ✏️ 编辑信息
        </el-button>
        <div v-else class="edit-actions">
          <el-button size="small" @click="cancelEdit">取消</el-button>
          <el-button type="primary" size="small" :loading="saving" @click="handleSaveProfile">
            保存
          </el-button>
        </div>
      </div>

      <!-- 头像区 -->
      <div class="avatar-row">
        <div class="avatar-circle">{{ avatarLetter() }}</div>
        <div class="avatar-info">
          <div class="avatar-name">{{ authStore.user?.nickname || authStore.user?.username || '—' }}</div>
          <div class="avatar-role">
            <el-tag
              size="small"
              :type="authStore.user?.role === 'super_admin' ? 'danger' : authStore.user?.role === 'admin' ? 'warning' : ''"
            >
              {{ roleLabel(authStore.user?.role) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 查看模式 -->
      <el-descriptions v-if="!editing" border :column="2" style="margin-top:20px">
        <el-descriptions-item label="用户名">
          {{ authStore.user?.username || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="昵称">
          {{ authStore.user?.nickname || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ authStore.user?.email || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          {{ authStore.user?.phone || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ authStore.user?.createTime || '—' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 编辑模式 -->
      <el-form v-else :model="editForm" label-width="80px" class="edit-form">
        <el-form-item label="用户名">
          <el-input :model-value="authStore.user?.username" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" placeholder="请输入昵称" maxlength="50" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" maxlength="100" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" maxlength="20" />
        </el-form-item>
      </el-form>

      <el-divider />

      <h3>⚙️ 适老化关怀设置</h3>
      <div class="elder-setting">
        <span>📖 字体放大30% + 高对比度</span>
        <el-switch
          :model-value="authStore.elderMode"
          active-text="已开启"
          inactive-text="已关闭"
          @change="handleElderModeChange"
        />
      </div>
      <p class="elder-desc">开启后界面字体增大，对比度优化</p>
    </el-card>

    <!-- ===== AI模型配置 ===== -->
    <el-card class="profile-card ai-model-card" style="margin-top:20px" v-loading="aiModelLoading">
      <template #header>
        <div class="profile-header">
          <h3>🤖 AI模型配置</h3>
          <el-tag v-if="aiModelExists" type="success" size="small">已配置 {{ aiModelApiKeyMasked }}</el-tag>
          <el-tag v-else type="info" size="small">未配置，使用系统默认模型</el-tag>
        </div>
      </template>

      <el-form :model="aiModelForm" label-width="110px" class="ai-model-form">
        <el-form-item label="启用配置">
          <el-switch
            v-model="aiModelForm.enabled"
            active-text="使用我的模型"
            inactive-text="使用系统默认"
          />
        </el-form-item>

        <el-form-item label="模型厂商">
          <el-select
            v-model="aiModelForm.provider"
            placeholder="请选择厂商"
            style="width: 100%"
            @change="applyProviderPreset"
          >
            <el-option label="阿里百炼 DashScope" value="dashscope" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Moonshot" value="moonshot" />
            <el-option label="自定义 OpenAI 兼容接口" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input
            v-model="aiModelForm.baseUrl"
            placeholder="例如 https://dashscope.aliyuncs.com/compatible-mode/v1"
          />
        </el-form-item>

        <el-form-item label="模型名称">
          <el-input v-model="aiModelForm.model" placeholder="例如 qwen3.6-plus" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="aiModelForm.apiKey"
            type="password"
            show-password
            :placeholder="aiModelExists ? `已保存 ${aiModelApiKeyMasked}，留空则不修改` : '请输入模型 API Key'"
          />
        </el-form-item>

        <div class="ai-param-grid">
          <el-form-item label="Temperature">
            <el-input-number
              v-model="aiModelForm.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :precision="2"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="Max Tokens">
            <el-input-number
              v-model="aiModelForm.maxTokens"
              :min="1"
              :max="200000"
              :step="256"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="Top P">
            <el-input-number
              v-model="aiModelForm.topP"
              :min="0"
              :max="1"
              :step="0.05"
              :precision="2"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <div class="ai-model-actions">
          <el-button
            v-if="aiModelExists"
            type="danger"
            plain
            :loading="aiModelDeleting"
            @click="handleDeleteAiModelConfig"
          >
            删除配置
          </el-button>
          <el-button type="primary" :loading="aiModelSaving" @click="handleSaveAiModelConfig">
            保存AI模型配置
          </el-button>
        </div>
      </el-form>
      <p class="ai-model-desc">
        配置保存后仅当前账号使用；API Key 会加密保存，页面只显示末尾掩码。
        AI导购会调用购物车、订单、页面跳转等工具，请选择支持 tools / function calling 的聊天模型。
      </p>
    </el-card>

    <!-- ===== 多模态图片识别配置 ===== -->
    <el-card class="profile-card ai-model-card" style="margin-top:20px" v-loading="multimodalLoading">
      <template #header>
        <div class="profile-header">
          <h3>🖼️ 图片识别模型配置</h3>
          <el-tag v-if="multimodalExists" type="success" size="small">已配置 {{ multimodalApiKeyMasked }}</el-tag>
          <el-tag v-else type="info" size="small">未配置，使用系统默认 DashScope Key</el-tag>
        </div>
      </template>

      <el-form :model="multimodalForm" label-width="110px" class="ai-model-form">
        <el-form-item label="启用配置">
          <el-switch
            v-model="multimodalForm.enabled"
            active-text="使用我的Key"
            inactive-text="使用系统默认"
          />
        </el-form-item>

        <el-form-item label="模型厂商">
          <el-input model-value="阿里百炼 DashScope（固定）" disabled />
        </el-form-item>

        <el-form-item label="模型用途">
          <el-input model-value="商品图片识别 / qwen3-vl-embedding 向量检索" disabled />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="multimodalForm.apiKey"
            type="password"
            show-password
            :placeholder="multimodalExists ? `已保存 ${multimodalApiKeyMasked}，留空则不修改` : '请输入阿里百炼 DashScope API Key'"
          />
        </el-form-item>

        <div class="ai-model-actions">
          <el-button
            v-if="multimodalExists"
            type="danger"
            plain
            :loading="multimodalDeleting"
            @click="handleDeleteMultimodalModelConfig"
          >
            删除配置
          </el-button>
          <el-button type="primary" :loading="multimodalSaving" @click="handleSaveMultimodalModelConfig">
            保存图片识别配置
          </el-button>
        </div>
      </el-form>
      <p class="ai-model-desc">
        此处只接受阿里百炼 DashScope API Key，不会使用 OpenAI、DeepSeek、Moonshot 等聊天模型厂商的 Key。
        图片识别向量库由 qwen3-vl-embedding 生成，查询图片也需要使用同一厂商的多模态向量能力。
      </p>
    </el-card>

    <!-- ===== 历史订单 ===== -->
    <el-card class="profile-card" style="margin-top:20px">
      <template #header>
        <h3>📜 历史订单</h3>
      </template>
      <el-table
        :data="orders"
        v-loading="loading"
        empty-text="暂无交易记录"
        @row-click="handleViewDetail"
        style="cursor:pointer"
      >
        <el-table-column prop="orderNo" label="订单号" />
        <el-table-column prop="createdAt" label="时间" />
        <el-table-column label="金额">
          <template #default="{ row }">{{ row.amount.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="itemsCount" label="件数" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '待支付'"
              type="primary"
              size="small"
              @click.stop="handlePay(row.id)"
            >
              去支付
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="ordersTotal > ordersPageSize"
        v-model:current-page="ordersPage"
        :page-size="ordersPageSize"
        :total="ordersTotal"
        layout="total, prev, pager, next"
        style="margin-top:16px;justify-content:flex-end"
      />
    </el-card>

    <!-- ===== 订单明细弹窗 ===== -->
    <el-dialog v-model="detailVisible" title="订单明细" width="560px" class="detail-dialog">
      <div v-if="detailLoading" style="text-align:center;padding:32px">加载中...</div>
      <template v-else-if="detailOrder">
        <el-descriptions border :column="2">
          <el-descriptions-item label="订单编号">{{ detailOrder.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailOrder.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="金额">{{ detailOrder.amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="件数">{{ detailOrder.itemsCount }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(detailOrder.status)">
              {{ detailOrder.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailOrder.paidAt" label="支付时间">
            {{ detailOrder.paidAt }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 style="margin:16px 0 8px">商品明细</h4>
        <el-table
          v-if="detailOrder.items && detailOrder.items.length > 0"
          :data="detailOrder.items"
          size="small"
        >
          <el-table-column prop="productName" label="商品" />
          <el-table-column label="单价">
            <template #default="{ row: r }">{{ r.price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="60" />
          <el-table-column label="小计">
            <template #default="{ row: r }">{{ r.subtotal.toFixed(2) }}</template>
          </el-table-column>
        </el-table>
        <div v-else style="text-align:center;padding:16px;color:#999">暂无明细</div>

        <div v-if="detailOrder.status === '待支付'" style="display:flex;justify-content:flex-end;gap:12px;margin-top:16px">
          <el-button type="danger" :loading="cancelling" @click="handleCancel(detailOrder.id)">
            取消订单
          </el-button>
          <el-button type="primary" @click="handlePay(detailOrder.id)">去支付</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.profile-page {
  animation: fadeIn 0.25s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.profile-card {
  border-radius: 20px;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.edit-actions {
  display: flex;
  gap: 8px;
}

/* ===== 头像区 ===== */
.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  padding: 8px 0;
}

.avatar-circle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677FF, #4096ff);
  color: #fff;
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1f2a3e;
}

.avatar-role {
  margin-top: 4px;
}

html.dark .avatar-name {
  color: #e0e0e0;
}

/* ===== 编辑表单 ===== */
.edit-form {
  margin-top: 20px;
}

/* ===== 适老化 ===== */
.elder-setting {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.elder-desc {
  color: #999;
  font-size: 0.85rem;
}

.detail-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid #eee;
}

.ai-model-form {
  max-width: 760px;
}

.ai-param-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.ai-model-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 4px;
}

.ai-model-desc {
  margin: 12px 0 0;
  color: #999;
  font-size: 0.85rem;
}

@media (max-width: 760px) {
  .ai-param-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }

  .ai-model-actions {
    justify-content: stretch;
  }

  .ai-model-actions .el-button {
    flex: 1;
  }
}
</style>
