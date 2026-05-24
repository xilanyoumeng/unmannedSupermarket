<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '../stores/cart'
import { createOrderApi } from '../api/order'
import { showToast } from '../composables/useToast'

const router = useRouter()
const cartStore = useCartStore()

const activeCartName = computed(() =>
  cartStore.carts.find(c => c.id === cartStore.activeCartId)?.name ?? ''
)

const checkingOut = ref(false)
const saving = ref(false)
const deleteVisible = ref(false)
const deleting = ref(false)

onMounted(async () => {
  await cartStore.fetchCart()
})

async function handleSelectCart(cartId: number) {
  await cartStore.selectCart(cartId)
}

function handleQuantityChange(itemId: number, newQty: number | undefined) {
  if (!newQty || newQty < 1) newQty = 1
  cartStore.updateQuantity(itemId, newQty)
}

function handleRemoveItem(itemId: number) {
  cartStore.removeItem(itemId)
}

async function handleSaveCart() {
  saving.value = true
  try {
    await cartStore.saveCart()
    showToast('购物车已保存', 'success')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    saving.value = false
  }
}

async function handleDeleteCart() {
  deleting.value = true
  try {
    await cartStore.clearCart()
    showToast('购物车已删除', 'success')
    deleteVisible.value = false
  } catch {
    // 错误已在拦截器中处理
  } finally {
    deleting.value = false
  }
}

async function handleCheckout() {
  if (cartStore.items.length === 0) {
    showToast('购物车为空，无法支付', 'warning')
    return
  }
  if (!cartStore.activeCartId) {
    showToast('请先选择购物车', 'warning')
    return
  }
  checkingOut.value = true
  try {
    const startTime = Date.now()
    const orderItems = cartStore.items.map(item => ({
      productId: item.productId,
      quantity: item.quantity
    }))
    await cartStore.saveCart()
    const orderRes = await createOrderApi({ items: orderItems })
    const order = orderRes.data.data
    router.push({
      name: 'OrderConfirm',
      params: { id: order.id },
      query: { startTime: startTime.toString() }
    })
  } catch {
    // 错误已在拦截器中处理
  } finally {
    checkingOut.value = false
  }
}
</script>

<template>
  <div class="cart-page">
    <el-card class="cart-card">
      <template #header>
        <div class="cart-header-row">
          <h2>🛍️ 购物车 · {{ activeCartName || '无感结算' }}</h2>
          <div class="cart-header-actions">
            <el-button
              v-if="cartStore.carts.length > 0"
              type="danger"
              plain
              size="small"
              @click="deleteVisible = true"
            >
              删除
            </el-button>
            <el-select
              v-if="cartStore.carts.length > 0"
              :model-value="cartStore.activeCartId"
              placeholder="选择购物车"
              style="width: 220px"
              @change="handleSelectCart"
            >
              <el-option
                v-for="cart in cartStore.carts"
                :key="cart.id"
                :label="cart.name"
                :value="cart.id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <div v-if="cartStore.carts.length === 0" class="empty-cart">
        🛒 购物车空空如也，去添加商品吧~
      </div>

      <div v-else-if="cartStore.items.length === 0" class="empty-cart">
        📦 当前购物车暂无商品
      </div>

      <template v-else>
        <el-table :data="cartStore.items" style="width:100%">
          <el-table-column prop="productName" label="商品" />
          <el-table-column label="单价">
            <template #default="{ row }">{{ row.productPrice.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="数量" width="140">
            <template #default="{ row }">
              <el-input-number
                :model-value="row.quantity"
                :min="1"
                size="small"
                @change="(val: number | undefined) => handleQuantityChange(row.id, val)"
              />
            </template>
          </el-table-column>
          <el-table-column label="小计">
            <template #default="{ row }">{{ (row.productPrice * row.quantity).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" text @click="handleRemoveItem(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="cart-footer">
          <span>商品总数：<strong>{{ cartStore.totalCount }}</strong> 件</span>
          <div class="cart-footer-right">
            <span class="total-price">{{ cartStore.totalPrice.toFixed(2) }}</span>
            <el-button type="primary" :loading="saving" @click="handleSaveCart">保存</el-button>
          </div>
        </div>

        <el-button
          type="primary"
          size="large"
          :loading="checkingOut"
          style="width:100%;margin-top:16px"
          @click="handleCheckout"
        >
          {{ checkingOut ? '支付处理中...' : '✅ 确认无感支付 (极速结算)' }}
        </el-button>
        <p class="checkout-note">无需扫码 · 自动扣款</p>
      </template>
    </el-card>

    <!-- ===== 删除购物车确认对话框 ===== -->
    <el-dialog v-model="deleteVisible" title="删除购物车" width="420px" class="delete-dialog">
      <el-form label-position="top">
        <el-form-item label="购物车名称">
          <el-input
            :model-value="cartStore.carts.find(c => c.id === cartStore.activeCartId)?.name ?? ''"
            disabled
          />
        </el-form-item>
        <el-form-item label="操作确认">
          <el-alert
            title="删除后购物车及其中所有商品明细将被永久移除，此操作不可恢复。"
            type="error"
            :closable="false"
            show-icon
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="handleDeleteCart">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cart-page {
  animation: fadeIn 0.25s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.cart-card {
  border-radius: 20px;
}

.cart-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cart-header-row h2 {
  margin: 0;
}

.cart-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.empty-cart {
  text-align: center;
  padding: 40px;
  color: #999;
}

.cart-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.cart-footer-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.total-price {
  font-size: 1.8rem;
  font-weight: bold;
  color: #1677FF;
}

.checkout-note {
  text-align: center;
  margin-top: 12px;
  font-size: 13px;
  color: #999;
}

.delete-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid #eee;
}

</style>
