<script setup lang="ts">
import { ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { getListedProductsApi, getHotProductsApi, getCategoriesApi, recognizeProductApi, getProductApi } from '../api/product'
import { useCartStore } from '../stores/cart'
import { useAuthStore } from '../stores/auth'
import { showToast } from '../composables/useToast'
import type { Product, HotProduct, RecognizeResponse } from '../types'
import type { UploadFile } from 'element-plus'

const cartStore = useCartStore()
const authStore = useAuthStore()

// ========== 热销商品 ==========
const hotProducts = ref<HotProduct[]>([])
const hotLoading = ref(false)

// ========== 分类（后端返回 string[]） ==========
const categories = ref<string[]>([])
const activeCategory = ref('')

// ========== 商品列表 ==========
const products = ref<Product[]>([])
const productsLoading = ref(false)
const productsPage = ref(1)
const productsTotal = ref(0)
const productsPageSize = 14

// ========== 商品详情 ==========
const detailVisible = ref(false)
const detailProduct = ref<Product | null>(null)
const detailLoading = ref(false)

// ========== AI识别 ==========
const recognizing = ref(false)
const recogResult = ref<RecognizeResponse | null>(null)
const selectedGoodsFile = ref<File | null>(null)
const selectedGoodsPreviewUrl = ref('')
const showRecogPanel = ref(false)

// ========== 添加到购物车状态 ==========
// ========== 数量选择对话框 ==========
const quantityVisible = ref(false)
const quantityProduct = ref<Product | null>(null)
const quantityCount = ref(1)
const quantitySubmitting = ref(false)

// ========== 加载热销商品 ==========
async function loadHotProducts() {
  hotLoading.value = true
  try {
    const res = await getHotProductsApi()
    const list = res.data.data ?? []
    list.sort((a, b) => (b.hotCount ?? 0) - (a.hotCount ?? 0))
    hotProducts.value = list.slice(0, 3)
  } catch { hotProducts.value = [] }
  finally { hotLoading.value = false }
}

// ========== 加载分类 ==========
async function loadCategories() {
  try {
    const res = await getCategoriesApi()
    categories.value = res.data.data ?? []
  } catch { categories.value = [] }
}

// ========== 加载商品列表 ==========
async function loadProducts() {
  productsLoading.value = true
  try {
    const res = await getListedProductsApi({
      page: productsPage.value,
      pageSize: productsPageSize,
      category: activeCategory.value || undefined
    })
    products.value = res.data.data?.records ?? []
    productsTotal.value = res.data.data?.total ?? 0
  } catch { products.value = [] }
  finally { productsLoading.value = false }
}

// ========== 切换分类 ==========
function handleCategoryChange(cat: string) {
  activeCategory.value = cat
  productsPage.value = 1
}

// ========== 查看商品详情 ==========
async function handleViewDetail(product: Product) {
  detailProduct.value = null
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res = await getProductApi(product.id)
    detailProduct.value = res.data.data
  } catch {
    detailProduct.value = product // 降级使用列表数据
  } finally { detailLoading.value = false }
}

// ========== 打开数量选择 ==========
function handleAddToCart(product: Product) {
  quantityProduct.value = product
  quantityCount.value = 1
  quantityVisible.value = true
}

async function confirmAddToCart() {
  const product = quantityProduct.value
  if (!product || quantitySubmitting.value) return
  quantitySubmitting.value = true
  try {
    await cartStore.addToCart(product.id, quantityCount.value)
    showToast(`${product.name} ×${quantityCount.value} 已加入购物车`, 'success')
    quantityVisible.value = false
  } catch { /* 拦截器已处理 */ }
  finally { quantitySubmitting.value = false }
}

// ========== AI识别 ==========
function handleGoodsFileChange(file: UploadFile) {
  if (selectedGoodsPreviewUrl.value) {
    URL.revokeObjectURL(selectedGoodsPreviewUrl.value)
  }
  selectedGoodsFile.value = file.raw as File
  selectedGoodsPreviewUrl.value = selectedGoodsFile.value
    ? URL.createObjectURL(selectedGoodsFile.value)
    : ''
}

async function handleRecognize() {
  if (!selectedGoodsFile.value) {
    showToast('请先上传商品图片', 'warning')
    return
  }
  recognizing.value = true
  recogResult.value = null
  try {
    if (!authStore.user && authStore.token) {
      await authStore.fetchUserProfile()
    }
    const formData = new FormData()
    formData.append('image', selectedGoodsFile.value)
    if (authStore.user?.id) {
      formData.append('user_id', String(authStore.user.id))
    }
    const res = await recognizeProductApi(formData)
    recogResult.value = res.data.data
  } catch { /* 拦截器已处理 */ }
  finally { recognizing.value = false }
}

function handleAddRecogToCart() {
  if (!recogResult.value || !recogResult.value.productId) return
  quantityProduct.value = {
    id: recogResult.value.productId,
    name: recogResult.value.name,
    price: recogResult.value.price
  } as Product
  quantityCount.value = 1
  quantityVisible.value = true
}

// ========== 初始化 ==========
onMounted(async () => {
  await Promise.all([loadHotProducts(), loadCategories(), loadProducts()])
  await cartStore.fetchCart()
})

onBeforeUnmount(() => {
  if (selectedGoodsPreviewUrl.value) {
    URL.revokeObjectURL(selectedGoodsPreviewUrl.value)
  }
})

watch(productsPage, () => loadProducts())
watch(activeCategory, () => loadProducts())
</script>

<template>
  <div class="shopping-page">
    <!-- ===== AI商品识别面板 ===== -->
    <el-card class="recog-card">
      <template #header>
        <div class="card-header-row">
          <h3>🔎 AI商品识别</h3>
          <el-button text type="primary" @click="showRecogPanel = !showRecogPanel">
            {{ showRecogPanel ? '收起' : '展开' }}
          </el-button>
        </div>
      </template>

      <div v-if="showRecogPanel" class="recog-body">
        <!-- 左半区：上传 -->
        <div class="recog-left">
          <div class="recog-section-title">📸 上传商品图片</div>
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleGoodsFileChange"
            accept="image/*"
            drag
            class="recog-uploader"
          >
            <div class="upload-drag-content">
              <span class="upload-icon">📸</span>
              <p>{{ selectedGoodsFile ? selectedGoodsFile.name : '点击或拖拽上传商品图片' }}</p>
            </div>
          </el-upload>
          <el-button
            type="primary"
            :loading="recognizing"
            @click="handleRecognize"
            class="recog-btn"
          >
            {{ recognizing ? '识别中...' : '一键识别商品' }}
          </el-button>
        </div>

        <!-- 右半区：识别结果 -->
        <div class="recog-right">
          <div class="recog-section-title">🔍 识别结果</div>
          <div v-if="recogResult" class="recog-result">
            <div class="recog-result-img" v-if="selectedGoodsPreviewUrl">
              <img :src="selectedGoodsPreviewUrl" alt="商品图片" />
            </div>
            <div class="recog-result-info">
              <span class="recog-label">商品名称</span>
              <span class="recog-name">{{ recogResult.name }}</span>
              <span class="recog-label">价格</span>
              <span class="recog-price">{{ recogResult.price.toFixed(2) }}</span>
              <span class="recog-label">置信度</span>
              <span class="recog-confidence">{{ (recogResult.confidence * 100).toFixed(1) }}%</span>
            </div>
            <el-button type="primary" @click="handleAddRecogToCart">
              ➕ 加入购物车
            </el-button>
          </div>
          <div v-else class="recog-placeholder">
            <span class="recog-placeholder-icon">🛒</span>
            <p>上传图片并点击识别后<br/>商品信息将显示在这里</p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ===== 热销商品 ===== -->
    <el-card class="hot-card">
      <template #header>
        <div class="card-header-row">
          <h3>🔥 热销商品</h3>
          <el-badge :value="cartStore.totalCount" class="cart-badge">
            <span class="badge-label">🛒 购物车</span>
          </el-badge>
        </div>
      </template>

      <div v-if="hotLoading" class="loading-text">加载中...</div>
      <div v-else-if="hotProducts.length === 0" class="empty-text">暂无热销商品</div>
      <div v-else class="hot-grid">
        <div
          v-for="(p, idx) in hotProducts"
          :key="p.id"
          class="hot-item"
          @click="handleViewDetail(p as unknown as Product)"
        >
          <div class="hot-rank">{{ ['🥇','🥈','🥉'][idx] }}</div>
          <el-image v-if="p.image" :src="p.image" fit="cover" class="hot-img" />
          <div v-else class="hot-emoji">📦</div>
          <div class="hot-info">
            <div class="hot-name">{{ p.name }}</div>
            <div class="hot-price">{{ p.price.toFixed(2) }}</div>
            <div class="hot-sales">热销 {{ p.hotCount ?? 0 }}</div>
          </div>
          <el-button
            type="primary"
            size="small"
            @click.stop="handleAddToCart(p as unknown as Product)"
          >
            ➕ 加入购物车
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ===== 商品导航栏 ===== -->
    <el-card class="products-card">
      <template #header>
        <el-tabs
          :model-value="activeCategory"
          @tab-change="handleCategoryChange"
          class="category-tabs"
        >
          <el-tab-pane label="全部商品" name="" />
          <el-tab-pane
            v-for="cat in categories"
            :key="cat"
            :label="cat"
            :name="cat"
          />
        </el-tabs>
      </template>

      <div v-if="productsLoading" class="loading-text">加载中...</div>
      <div v-else-if="products.length === 0" class="empty-text">该分类暂无商品</div>
      <div v-else class="product-grid">
        <el-card
          v-for="p in products"
          :key="p.id"
          shadow="hover"
          class="product-card"
          @click="handleViewDetail(p)"
        >
          <div class="product-img-wrap">
            <el-image v-if="p.image" :src="p.image" fit="cover" class="product-img" />
            <div class="product-emoji">📦</div>
          </div>
          <div class="product-name">{{ p.name }}</div>
          <div class="product-category">{{ p.category }}</div>
          <div class="product-price">{{ p.price.toFixed(2) }}</div>
          <div class="product-stock">库存 {{ p.stock }}</div>
          <el-button
            type="primary"
            size="small"
            @click.stop="handleAddToCart(p)"
          >
            ➕ 加入购物车
          </el-button>
        </el-card>
      </div>

      <div class="pagination-bar">
        <span class="pagination-total">共 {{ productsTotal }} 件商品</span>
        <el-pagination
          v-if="productsTotal > productsPageSize"
          v-model:current-page="productsPage"
          :page-size="productsPageSize"
          :total="productsTotal"
          layout="prev, pager, next"
          class="pagination-wrap"
        />
      </div>
    </el-card>

    <!-- ===== 商品详情弹窗 ===== -->
    <el-dialog
      v-model="detailVisible"
      :title="detailProduct?.name ?? '商品详情'"
      width="560px"
      class="detail-dialog"
    >
      <div v-if="detailLoading" class="loading-text">加载中...</div>
      <div v-else-if="detailProduct" class="detail-body">
        <div class="detail-img-wrap">
          <el-image
            v-if="detailProduct.image"
            :src="detailProduct.image"
            fit="contain"
            class="detail-img"
          />
          <div v-else class="detail-emoji">📦</div>
        </div>
        <div class="detail-info">
          <div class="detail-row">
            <span class="detail-label">商品名称</span>
            <span class="detail-value">{{ detailProduct.name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">分类</span>
            <el-tag size="small">{{ detailProduct.category }}</el-tag>
          </div>
          <div class="detail-row">
            <span class="detail-label">价格</span>
            <span class="detail-price">{{ detailProduct.price.toFixed(2) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">库存</span>
            <span class="detail-value">{{ detailProduct.stock }} 件</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">条码</span>
            <span class="detail-value">{{ detailProduct.barcode }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">描述</span>
            <span class="detail-value">{{ detailProduct.description || '暂无描述' }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button
          type="primary"
          @click="detailProduct && (detailVisible = false) && handleAddToCart(detailProduct)"
        >
          ➕ 加入购物车
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 数量选择对话框 ===== -->
    <el-dialog v-model="quantityVisible" title="添加商品到购物车" width="380px" class="quantity-dialog">
      <div v-if="quantityProduct" class="quantity-body">
        <div class="quantity-product-name">{{ quantityProduct.name }}</div>
        <div class="quantity-product-price">单价 {{ quantityProduct.price.toFixed(2) }}</div>

        <div class="quantity-row">
          <span class="quantity-label">选择数量</span>
          <el-input-number
            v-model="quantityCount"
            :min="1"
            :max="quantityProduct.stock || 999"
            size="default"
          />
        </div>

        <div class="quantity-total">
          合计 <span class="quantity-total-price">{{ (quantityProduct.price * quantityCount).toFixed(2) }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="quantityVisible = false">取消</el-button>
        <el-button type="primary" :loading="quantitySubmitting" @click="confirmAddToCart">
          确认加入购物车
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.shopping-page {
  animation: fadeIn 0.25s;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== 通用卡片头 ===== */
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-row h3 {
  margin: 0;
}

/* ===== AI识别卡片 ===== */
.recog-card {
  border-radius: 20px;
}

.recog-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.recog-section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #5A6874;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

/* 左半区：上传 */
.recog-left {
  display: flex;
  flex-direction: column;
}

.recog-uploader {
  width: 100%;
}

.upload-drag-content {
  text-align: center;
  padding: 20px 0;
}

.upload-icon {
  font-size: 2.4rem;
}

.upload-drag-content p {
  margin-top: 8px;
  color: #999;
}

.recog-btn {
  width: 100%;
  margin-top: 12px;
}

/* 右半区：识别结果 */
.recog-right {
  display: flex;
  flex-direction: column;
  min-height: 200px;
}

.recog-result {
  flex: 1;
  background: #f0f6ff;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recog-result-img {
  width: 100%;
  max-height: 150px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.recog-result-img img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.recog-result-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recog-label {
  font-size: 0.75rem;
  color: #999;
  margin-top: 6px;
}

.recog-label:first-child {
  margin-top: 0;
}

.recog-name {
  font-size: 1.1rem;
  font-weight: 600;
}

.recog-price {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1677FF;
}

.recog-confidence {
  font-size: 0.85rem;
  color: #52c41a;
}

/* 右半区占位 */
.recog-placeholder {
  flex: 1;
  background: #fafafa;
  border: 2px dashed #e0e0e0;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 200px;
}

.recog-placeholder-icon {
  font-size: 2.4rem;
  opacity: 0.5;
}

.recog-placeholder p {
  margin: 0;
  text-align: center;
  color: #bbb;
  font-size: 0.85rem;
  line-height: 1.5;
}

/* ===== 热销商品 ===== */
.hot-card {
  border-radius: 20px;
}

.cart-badge {
  margin-right: 8px;
}

.badge-label {
  padding: 0 4px;
  color: #5A6874;
}

.hot-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.hot-item {
  background: linear-gradient(135deg, #fff7ed 0%, #fff1f2 100%);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}

.hot-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(255, 77, 79, 0.15);
}

.hot-rank {
  position: absolute;
  top: -4px;
  left: 12px;
  font-size: 1.2rem;
}

.hot-img {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  flex-shrink: 0;
}

.hot-emoji {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  flex-shrink: 0;
}

.hot-info {
  flex: 1;
  min-width: 0;
}

.hot-name {
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hot-price {
  color: #1677FF;
  font-weight: 700;
  font-size: 1.1rem;
}

.hot-sales {
  color: #ff4d4f;
  font-size: 0.75rem;
}

/* ===== 分类导航选项卡 ===== */
.category-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.category-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

/* ===== 商品列表 ===== */
.products-card {
  border-radius: 20px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 14px;
}

.product-card {
  text-align: center;
  border-radius: 16px;
  cursor: pointer;
  transition: transform 0.2s;
}

.product-card:hover {
  transform: translateY(-4px);
}

.product-card :deep(.el-card__body) {
  padding: 16px;
}

.product-img-wrap {
  position: relative;
}

.product-img {
  width: 80px;
  height: 80px;
  border-radius: 12px;
  margin-bottom: 6px;
}

.product-emoji {
  width: 80px;
  height: 80px;
  border-radius: 12px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  margin: 0 auto 6px;
}

.product-name {
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.product-category {
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 4px;
}

.product-price {
  color: #1677FF;
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: 2px;
}

.product-stock {
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 8px;
}

.pagination-bar {
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

.pagination-wrap {
  flex-shrink: 0;
}

/* ===== 商品详情弹窗 ===== */
.detail-dialog :deep(.el-dialog__body) {
  padding-top: 12px;
}

.detail-body {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.detail-img-wrap {
  flex-shrink: 0;
}

.detail-img {
  width: 200px;
  height: 200px;
  border-radius: 16px;
  background: #f5f5f5;
}

.detail-emoji {
  width: 200px;
  height: 200px;
  border-radius: 16px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
}

.detail-info {
  flex: 1;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-label {
  width: 64px;
  flex-shrink: 0;
  color: #999;
  font-size: 0.9rem;
}

.detail-value {
  color: #1F2A3E;
}

.detail-price {
  font-size: 1.6rem;
  font-weight: 700;
  color: #1677FF;
}

/* ===== 通用状态文本 ===== */
.loading-text, .empty-text {
  text-align: center;
  padding: 40px;
  color: #999;
}

/* ===== 数量选择对话框 ===== */
.quantity-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quantity-product-name {
  font-size: 1.1rem;
  font-weight: 600;
}

.quantity-product-price {
  color: #999;
  font-size: 0.85rem;
}

.quantity-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quantity-label {
  font-size: 0.95rem;
  color: #333;
}

.quantity-total {
  text-align: right;
  padding-top: 12px;
  border-top: 1px solid #eee;
  font-size: 1rem;
}

.quantity-total-price {
  font-size: 1.6rem;
  font-weight: 700;
  color: #1677FF;
  margin-left: 8px;
}

/* ===== 夜间模式覆盖 ===== */
html.dark .hot-item {
  background: linear-gradient(135deg, #2a1f1f 0%, #1f1f2a 100%);
}

html.dark .recog-result {
  background: #1a2740;
}

html.dark .recog-result-img {
  background: #2a2a2a;
}

html.dark .recog-placeholder {
  background: #1a1a1a;
  border-color: #333;
}

html.dark .recog-placeholder p {
  color: #666;
}

html.dark .recog-section-title {
  color: #b0b8c2;
  border-bottom-color: #333;
}

html.dark .hot-emoji,
html.dark .product-emoji,
html.dark .detail-emoji {
  background: #2a2a2a;
}

html.dark .detail-value {
  color: #e0e0e0;
}

html.dark .badge-label {
  color: #b0b8c2;
}

@media (max-width: 800px) {
  .hot-grid {
    grid-template-columns: 1fr;
  }

  .recog-body {
    grid-template-columns: 1fr;
  }
}
</style>
