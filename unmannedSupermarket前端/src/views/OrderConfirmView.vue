<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getOrderApi, payOrderApi } from '../api/order'
import { useCartStore } from '../stores/cart'
import { showToast } from '../composables/useToast'
import type { Order } from '../types'

const PAYMENT_WINDOW_MS = 15 * 60 * 1000

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()

const orderId = Number(route.params.id)
const order = ref<Order | null>(null)
const loading = ref(false)
const paying = ref(false)

const now = ref(Date.now())
let timer: ReturnType<typeof setInterval> | null = null

const startTimeMs = Number(route.query.startTime) || 0

const expireTimeMs = computed(() => {
  const base = startTimeMs || (order.value?.createdAt ? new Date(order.value.createdAt).getTime() : 0)
  if (!base) return 0
  return base + PAYMENT_WINDOW_MS
})

const remainingMs = computed(() => Math.max(0, expireTimeMs.value - now.value))

const remainingText = computed(() => {
  const ms = remainingMs.value
  const m = Math.floor(ms / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const isExpired = computed(() => remainingMs.value <= 0)

onMounted(async () => {
  loading.value = true
  try {
    const res = await getOrderApi(orderId)
    order.value = res.data.data
  } catch {
    showToast('订单加载失败', 'error')
  } finally {
    loading.value = false
  }
  timer = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})

async function handlePay() {
  if (isExpired.value) {
    showToast('订单已超时，无法支付', 'warning')
    return
  }
  paying.value = true
  try {
    const payRes = await payOrderApi(orderId)
    const data = payRes.data.data
    await cartStore.clearCart()
    router.push({
      name: 'PaymentSuccess',
      query: {
        orderNo: data.orderNo,
        amount: data.amount.toString(),
        paidAt: data.paidAt
      }
    })
  } catch {
    // 错误已在拦截器中处理
  } finally {
    paying.value = false
  }
}
</script>

<template>
  <div class="order-confirm-page">
    <el-card class="order-card">
      <template #header>
        <div class="card-header-row">
          <h2>📋 订单确认</h2>
          <div v-if="order && order.status === '待支付'" class="countdown-box">
            <span class="countdown-label">剩余支付时间</span>
            <span class="countdown-time" :class="{ expired: isExpired }">
              {{ isExpired ? '已超时' : remainingText }}
            </span>
          </div>
        </div>
      </template>

      <div v-if="loading" class="loading-text">加载中...</div>

      <template v-else-if="order">
        <el-descriptions border :column="2">
          <el-descriptions-item label="订单编号">{{ order.orderNo }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ order.username ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ order.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="order.status === '待支付' && !isExpired" type="warning">待支付</el-tag>
            <el-tag v-else-if="order.status === '待支付' && isExpired" type="danger">已超时</el-tag>
            <el-tag v-else-if="order.status === '已支付'" type="success">已支付</el-tag>
            <el-tag v-else type="info">已取消</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="order.status === '待支付' && isExpired"
          title="该订单已超过15分钟支付有效期，请重新下单"
          type="error"
          :closable="false"
          show-icon
          style="margin-top:12px"
        />

        <h3 class="items-title">商品明细</h3>
        <el-table v-if="order.items && order.items.length > 0" :data="order.items" style="width:100%">
          <el-table-column prop="productName" label="商品" />
          <el-table-column label="单价">
            <template #default="{ row: r }">{{ r.price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column label="小计">
            <template #default="{ row: r }">{{ (r.price * r.quantity).toFixed(2) }}</template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-text">暂无明细</div>

        <div class="order-total">
          合计 <span class="total-price">{{ order.amount.toFixed(2) }}</span>
        </div>

        <div class="pay-actions">
          <el-button @click="router.back()">返回</el-button>
          <el-button
            v-if="order.status === '待支付'"
            type="danger"
            size="large"
            :loading="paying"
            :disabled="isExpired"
            @click="handlePay"
          >
            {{ paying ? '支付处理中...' : '💳 确认支付' }}
          </el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped>
.order-confirm-page {
  animation: fadeIn 0.25s;
  display: flex;
  justify-content: center;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.order-card {
  max-width: 680px;
  width: 100%;
  border-radius: 20px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-row h2 {
  margin: 0;
}

.countdown-box {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.countdown-label {
  font-size: 0.8rem;
  color: #999;
}

.countdown-time {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1677FF;
  font-variant-numeric: tabular-nums;
}

.countdown-time.expired {
  color: #F56C6C;
  font-size: 1rem;
}

.items-title {
  margin: 20px 0 12px;
}

.order-total {
  text-align: right;
  padding-top: 16px;
  border-top: 1px solid #eee;
  margin-top: 16px;
  font-size: 1rem;
}

.total-price {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1677FF;
  margin-left: 8px;
}

.pay-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.loading-text, .empty-text {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
