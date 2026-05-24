<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const orderNo = (route.query.orderNo as string) || '—'
const amount = parseFloat((route.query.amount as string) || '0')
const paidAt = (route.query.paidAt as string) || new Date().toLocaleString()
</script>

<template>
  <div class="success-page">
    <el-card class="success-card">
      <el-result
        icon="success"
        title="支付成功"
        :sub-title="'订单号：' + orderNo"
      >
        <template #extra>
          <el-descriptions border :column="1" style="margin-bottom:24px">
            <el-descriptions-item label="订单号">{{ orderNo }}</el-descriptions-item>
            <el-descriptions-item label="支付时间">{{ paidAt }}</el-descriptions-item>
            <el-descriptions-item label="支付方式">眸界无感智付</el-descriptions-item>
            <el-descriptions-item label="实付金额">
              <span class="amount-text">{{ amount.toFixed(2) }}</span>
            </el-descriptions-item>
          </el-descriptions>

          <div class="action-btns">
            <el-button type="primary" @click="router.push('/shopping')">继续购物</el-button>
            <el-button @click="router.push('/profile')">查看订单</el-button>
          </div>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<style scoped>
.success-page {
  animation: fadeIn 0.25s;
  display: flex;
  justify-content: center;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.success-card {
  max-width: 560px;
  width: 100%;
  border-radius: 20px;
}

.amount-text {
  color: #2BAF2B;
  font-weight: bold;
  font-size: 1.2rem;
}

.action-btns {
  display: flex;
  gap: 16px;
  justify-content: center;
}
</style>
