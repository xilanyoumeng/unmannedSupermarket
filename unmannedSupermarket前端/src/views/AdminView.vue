<script setup lang="ts">
import { ref, watch } from 'vue'
import { getUserPageApi, updateUserRoleApi, deleteUserApi, adminResetPasswordApi } from '../api/user'
import { getAllOrdersApi, getOrdersByStatusApi, getOrderApi } from '../api/order'
import type { UserInfo, Order } from '../types'
import ProductManage from '../components/ProductManage.vue'
import { showToast, showConfirm } from '../composables/useToast'
import { useAuthStore } from '../stores/auth'

type AdminTab = 'goods' | 'users' | 'orders'

const authStore = useAuthStore()
const activeTab = ref<AdminTab>('goods')

// 用户管理
const users = ref<UserInfo[]>([])
const usersLoading = ref(false)
const usersPage = ref(1)
const usersTotal = ref(0)
const usersPageSize = 10

// 角色编辑弹窗
const roleDialogVisible = ref(false)
const roleEditingUser = ref<UserInfo | null>(null)
const roleSelected = ref('')

// 重置密码
const resetPwdLoading = ref(false)

// 订单管理
const orders = ref<Order[]>([])
const ordersLoading = ref(false)
const ordersPage = ref(1)
const ordersTotal = ref(0)
const ordersPageSize = 10
const orderStatusFilter = ref('')

// 订单详情弹窗
const orderDetailVisible = ref(false)
const orderDetail = ref<Order | null>(null)
const orderDetailLoading = ref(false)

async function loadUsers() {
  usersLoading.value = true
  try {
    const res = await getUserPageApi(usersPage.value, usersPageSize)
    users.value = res.data.data?.records ?? []
    usersTotal.value = res.data.data?.total ?? 0
  } catch {
    users.value = []
  } finally {
    usersLoading.value = false
  }
}

function openRoleEdit(row: UserInfo) {
  roleEditingUser.value = row
  roleSelected.value = row.role ?? 'user'
  roleDialogVisible.value = true
}

async function handleRoleSave() {
  if (!roleEditingUser.value) return
  try {
    await updateUserRoleApi(roleEditingUser.value.id, roleSelected.value)
    showToast('角色修改成功', 'success')
    roleDialogVisible.value = false
    await loadUsers()
  } catch {
    // 错误已在拦截器中处理
  }
}

async function handleDeleteUser(row: UserInfo) {
  if (!(await showConfirm(`确定要删除用户"${row.nickname || row.username}"吗？此操作不可撤销。`, '删除用户'))) return
  try {
    await deleteUserApi(row.id)
    showToast('用户已删除', 'success')
    await loadUsers()
  } catch {
    // 错误已在拦截器中处理
  }
}

async function handleResetPwd(row: UserInfo) {
  if (!(await showConfirm(`确定要重置用户"${row.nickname || row.username}"的密码吗？密码将被重置为默认密码。`, '重置密码'))) return
  resetPwdLoading.value = true
  try {
    await adminResetPasswordApi(row.id)
    showToast('密码已重置为默认密码', 'success')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    resetPwdLoading.value = false
  }
}

async function loadOrders() {
  ordersLoading.value = true
  try {
    const pageParams = {
      page: ordersPage.value,
      pageSize: ordersPageSize
    }
    const res = orderStatusFilter.value
      ? await getOrdersByStatusApi(orderStatusFilter.value, pageParams)
      : await getAllOrdersApi(pageParams)
    orders.value = res.data.data?.records ?? []
    ordersTotal.value = res.data.data?.total ?? 0
  } catch {
    orders.value = []
  } finally {
    ordersLoading.value = false
  }
}

async function openOrderDetail(row: Order) {
  orderDetailVisible.value = true
  orderDetailLoading.value = true
  try {
    const res = await getOrderApi(row.id)
    orderDetail.value = res.data.data
  } catch {
    orderDetail.value = null
  } finally {
    orderDetailLoading.value = false
  }
}

function handleTabSelect(index: string) {
  activeTab.value = index as AdminTab
}

function statusTagType(status: string) {
  if (status === '已支付') return 'success'
  if (status === '待支付') return 'warning'
  return 'info'
}

// Tab 切换时按需加载
watch(activeTab, (tab) => {
  if (tab === 'users') loadUsers()
  if (tab === 'orders') loadOrders()
})

// 分页变化时重新加载
watch(usersPage, () => loadUsers())
watch(ordersPage, () => loadOrders())
</script>

<template>
  <div class="admin-page">
    <div class="admin-layout">
      <!-- 侧栏 -->
      <el-menu
        :default-active="activeTab"
        class="admin-sidebar"
        @select="handleTabSelect"
      >
        <el-menu-item index="goods">📦 商品管理</el-menu-item>
        <el-menu-item index="users">👥 用户管理</el-menu-item>
        <el-menu-item index="orders">📋 订单管理</el-menu-item>
      </el-menu>

      <!-- 内容区 -->
      <div class="admin-content">
        <!-- 商品管理 -->
        <div v-if="activeTab === 'goods'">
          <h3>商品清单</h3>
          <ProductManage />
        </div>

        <!-- 用户管理 -->
        <div v-if="activeTab === 'users'">
          <h3>注册用户</h3>

          <el-table :data="users" v-loading="usersLoading" empty-text="暂无用户数据">
            <el-table-column type="index" label="序号" width="70" />
            <el-table-column prop="username" label="用户名" />
            <el-table-column prop="nickname" label="昵称" />
            <el-table-column prop="role" label="角色" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.role === 'super_admin'" type="danger" size="small">超级管理员</el-tag>
                <el-tag v-else-if="row.role === 'admin'" type="warning" size="small">管理员</el-tag>
                <el-tag v-else type="info" size="small">用户</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="注册时间" />
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  text
                  size="small"
                  :disabled="row.role === 'super_admin' || row.id === authStore.user?.id || (authStore.user?.role === 'admin' && row.role === 'admin')"
                  @click="openRoleEdit(row)"
                >
                  修改角色
                </el-button>
                <el-button
                  v-if="authStore.user?.role === 'super_admin'"
                  type="warning"
                  text
                  size="small"
                  :disabled="row.id === authStore.user?.id"
                  @click="handleResetPwd(row)"
                >
                  重置密码
                </el-button>
                <el-button
                  type="danger"
                  text
                  size="small"
                  :disabled="row.role === 'super_admin' || row.id === authStore.user?.id || (authStore.user?.role === 'admin' && row.role === 'admin')"
                  @click="handleDeleteUser(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-row">
            <span class="pagination-total">共 {{ usersTotal }} 位用户</span>
            <el-pagination
              v-if="usersTotal > usersPageSize"
              v-model:current-page="usersPage"
              :page-size="usersPageSize"
              :total="usersTotal"
              layout="prev, pager, next"
            />
          </div>
        </div>

        <!-- 角色编辑弹窗 -->
        <el-dialog v-model="roleDialogVisible" title="修改用户角色" width="400px">
          <div style="margin-bottom: 12px">
            <span>用户：</span>
            <strong>{{ roleEditingUser?.nickname || roleEditingUser?.username }}</strong>
          </div>
          <el-radio-group v-model="roleSelected">
            <el-radio value="user">用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
          <template #footer>
            <el-button @click="roleDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleRoleSave">保存</el-button>
          </template>
        </el-dialog>

        <!-- 订单管理 -->
        <div v-if="activeTab === 'orders'">
          <div class="content-header">
            <h3>订单管理</h3>
            <el-select
              v-model="orderStatusFilter"
              placeholder="筛选状态"
              clearable
              style="width:140px"
              @change="ordersPage = 1; loadOrders()"
            >
              <el-option label="全部" value="" />
              <el-option label="待支付" value="PENDING_PAYMENT" />
              <el-option label="已支付" value="PAID" />
              <el-option label="已取消" value="CANCELLED" />
            </el-select>
          </div>

          <el-table :data="orders" v-loading="ordersLoading" empty-text="暂无订单数据">
            <el-table-column type="index" label="序号" width="70" />
            <el-table-column prop="orderNo" label="订单号" />
            <el-table-column prop="username" label="下单人" width="120" />
            <el-table-column label="金额" width="120">
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
            <el-table-column prop="createdAt" label="创建时间" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" text size="small" @click="openOrderDetail(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-row">
            <span class="pagination-total">共 {{ ordersTotal }} 条订单</span>
            <el-pagination
              v-if="ordersTotal > ordersPageSize"
              v-model:current-page="ordersPage"
              :page-size="ordersPageSize"
              :total="ordersTotal"
              layout="prev, pager, next"
            />
          </div>

          <!-- 订单详情弹窗 -->
          <el-dialog v-model="orderDetailVisible" title="订单详情" width="560px">
            <div v-loading="orderDetailLoading">
              <template v-if="orderDetail">
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="订单号">{{ orderDetail.orderNo }}</el-descriptions-item>
                  <el-descriptions-item label="下单人">{{ orderDetail.username }}</el-descriptions-item>
                  <el-descriptions-item label="金额">{{ orderDetail.amount.toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item label="件数">{{ orderDetail.itemsCount }}</el-descriptions-item>
                  <el-descriptions-item label="状态">
                    <el-tag :type="statusTagType(orderDetail.status)">{{ orderDetail.status }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="创建时间">{{ orderDetail.createdAt }}</el-descriptions-item>
                </el-descriptions>
                <h4 style="margin: 16px 0 8px">商品明细</h4>
                <el-table :data="orderDetail.items" size="small">
                  <el-table-column type="index" label="序号" width="60" />
                  <el-table-column prop="productName" label="商品名称" />
                  <el-table-column prop="price" label="单价" width="100">
                    <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
                  </el-table-column>
                  <el-table-column prop="quantity" label="数量" width="80" />
                  <el-table-column prop="subtotal" label="小计" width="100">
                    <template #default="{ row }">{{ row.subtotal.toFixed(2) }}</template>
                  </el-table-column>
                </el-table>
              </template>
              <el-empty v-else description="暂无订单数据" />
            </div>
          </el-dialog>

        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  animation: fadeIn 0.25s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.admin-layout {
  display: flex;
  gap: 20px;
}

.admin-sidebar {
  width: 200px;
  border-radius: 16px;
  flex-shrink: 0;
  overflow: hidden;
}

.admin-content {
  flex: 1;
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  min-height: 400px;
}

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 16px;
  gap: 12px;
}

.pagination-total {
  font-size: 0.85rem;
  color: #999;
  white-space: nowrap;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}


@media (max-width: 800px) {
  .admin-layout {
    flex-direction: column;
  }
  .admin-sidebar {
    width: 100%;
  }
  .admin-sidebar :deep(.el-menu-item) {
    justify-content: center;
  }
}
</style>
