<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProductsApi, createProductApi, updateProductApi, deleteProductApi, updateProductStatusApi, getCategoriesApi } from '../api/product'
import { uploadImageApi } from '../api/upload'
import { showToast, showConfirm } from '../composables/useToast'
import type { Product, ProductForm } from '../types'

const emit = defineEmits<{
  (e: 'updated'): void
}>()

// 分类列表
const categories = ref<string[]>([])

// 分页查询
const tableData = ref<Product[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 查询条件
const keyword = ref('')
const category = ref('')

// 表单弹窗
const dialogVisible = ref(false)
const dialogTitle = ref('')
const editingId = ref<number | null>(null)
const form = ref<ProductForm>({
  name: '',
  price: 0,
  stock: 0,
  category: '',
  description: '',
  image: '',
  barcode: ''
})
const saving = ref(false)
const uploading = ref(false)

// 图片上传
function handleFileSelect(uploadFile: any) {
  const file = uploadFile.raw as File
  if (!file || !file.type.startsWith('image/')) {
    showToast('请选择图片文件', 'warning')
    return
  }
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  uploadImageApi(fd)
    .then((res) => {
      form.value.image = res.data.data.url
      showToast('图片上传成功', 'success')
    })
    .catch(() => {
      // 错误已在拦截器中处理
    })
    .finally(() => {
      uploading.value = false
    })
}

onMounted(() => {
  loadCategories()
  fetchData()
})

async function loadCategories() {
  try {
    const res = await getCategoriesApi()
    categories.value = res.data.data ?? []
  } catch { categories.value = [] }
}

async function fetchData() {
  loading.value = true
  try {
    const params: { page: number; pageSize: number; keyword?: string; category?: string } = {
      page: page.value,
      pageSize: pageSize.value
    }
    if (keyword.value) params.keyword = keyword.value
    if (category.value) params.category = category.value
    const res = await getProductsApi(params)
    tableData.value = res.data.data?.records ?? []
    total.value = res.data.data?.total ?? 0
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleReset() {
  keyword.value = ''
  category.value = ''
  page.value = 1
  fetchData()
}

function handleSizeChange(val: number) {
  pageSize.value = val
  page.value = 1
  fetchData()
}

function handleCurrentChange(val: number) {
  page.value = val
  fetchData()
}

// 新增 / 编辑
function openAdd() {
  dialogTitle.value = '新增商品'
  editingId.value = null
  form.value = { name: '', price: 0, stock: 0, category: '', description: '', image: '', barcode: '' }
  dialogVisible.value = true
}

function openEdit(row: Product) {
  dialogTitle.value = '修改商品'
  editingId.value = row.id
  form.value = {
    name: row.name,
    price: row.price,
    stock: row.stock,
    category: row.category,
    description: row.description,
    image: row.image,
    barcode: row.barcode
  }
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
  editingId.value = null
}

async function handleSave() {
  if (!form.value.name.trim()) {
    showToast('请输入商品名称', 'warning')
    return
  }
  if (form.value.price <= 0) {
    showToast('请输入有效价格', 'warning')
    return
  }

  saving.value = true
  try {
    if (editingId.value != null) {
      await updateProductApi(editingId.value, form.value)
      showToast('商品修改成功', 'success')
    } else {
      await createProductApi(form.value)
      showToast('商品添加成功', 'success')
    }
    dialogVisible.value = false
    editingId.value = null
    emit('updated')
    await fetchData()
  } catch {
    // 错误已在拦截器中处理
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: Product) {
  if (!(await showConfirm(`确定要删除商品"${row.name}"吗？此操作不可撤销。`, '删除商品'))) return
  try {
    await deleteProductApi(row.id)
    showToast('商品已删除', 'success')
    emit('updated')
    await fetchData()
  } catch {
    // 错误已在拦截器中处理
  }
}

async function handleToggleStatus(row: Product) {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await updateProductStatusApi(row.id, newStatus)
    showToast(`商品已${newStatus === 0 ? '下架' : '上架'}`, 'success')
    emit('updated')
    await fetchData()
  } catch {
    // 错误已在拦截器中处理
  }
}

function productStatusLabel(status: number) {
  return status === 1 ? '上架' : '下架'
}

function productStatusType(status: number) {
  return status === 1 ? 'success' : 'info'
}
</script>

<template>
  <div class="product-manage">
    <!-- 查询区域 -->
    <div class="search-bar">
      <el-form :inline="true" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="keyword"
            placeholder="搜索商品名称或描述"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select
            v-model="category"
            placeholder="全部分类"
            clearable
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="openAdd">+ 新增商品</el-button>
    </div>

    <!-- 数据表格 -->
    <el-table :data="tableData" v-loading="loading" empty-text="暂无商品数据" stripe border>
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column label="图片" width="80" align="center">
        <template #default="{ row }">
          <el-image
            v-if="row.image"
            :src="row.image"
            style="width: 48px; height: 48px; border-radius: 6px"
            fit="cover"
            :preview-src-list="[row.image]"
          />
          <span v-else class="no-image">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="商品名称" min-width="140" show-overflow-tooltip />
      <el-table-column prop="barcode" label="条形码" width="140" show-overflow-tooltip />
      <el-table-column label="价格" width="100" align="right">
        <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="库存" width="80" align="center">
        <template #default="{ row }">
          <span :class="{ 'low-stock': row.stock < 10 }">{{ row.stock }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="100" align="center">
        <template #default="{ row }">{{ row.category || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="productStatusType(row.status)" size="small">
            {{ productStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170" align="center">
        <template #default="{ row }">{{ row.updateTime || row.createTime || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" text size="small" @click="openEdit(row)">修改</el-button>
          <el-button
            :type="row.status === 1 ? 'warning' : 'success'"
            text
            size="small"
            @click="handleToggleStatus(row)"
          >
            {{ row.status === 1 ? '下架' : '上架' }}
          </el-button>
          <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar">
      <span class="pagination-total">共 {{ total }} 件商品</span>
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[5, 10, 20, 50]"
        :total="total"
        layout="sizes, prev, pager, next, jumper"
        background
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="460px"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="商品名称">
          <el-input v-model="form.name" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="价格">
          <el-input-number v-model="form.price" :min="0" :precision="2" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="库存">
          <el-input-number v-model="form.stock" :min="0" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="条形码">
          <el-input v-model="form.barcode" placeholder="商品条形码" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select
            v-model="form.category"
            placeholder="请选择分类"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="选填" />
        </el-form-item>
        <el-form-item label="商品图片">
          <div class="image-upload">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              :on-change="handleFileSelect"
              class="image-upload-trigger"
            >
              <div class="image-preview" v-if="form.image" v-loading="uploading">
                <el-image :src="form.image" fit="cover" />
                <div class="image-mask">
                  <span class="image-mask-x">✕</span>
                </div>
              </div>
              <div class="image-placeholder" v-else v-loading="uploading">
                <span class="image-placeholder-plus">+</span>
                <span class="image-placeholder-text">点击上传图片</span>
              </div>
            </el-upload>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ saving ? '保存中...' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.product-manage {
  /* 组件容器 */
}

/* 查询区域 */
.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: #f8fafe;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.search-form {
  margin-bottom: 0;
}

.search-form :deep(.el-form-item) {
  margin-bottom: 0;
}

/* 分页栏 */
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

.low-stock {
  color: #dc2626;
  font-weight: 600;
}

.no-image {
  color: #bbb;
  font-size: 0.85rem;
}

/* 图片上传 */
.image-upload-trigger {
  display: block;
}

.image-upload-trigger :deep(.el-upload) {
  display: block;
}

.image-preview {
  position: relative;
  width: 200px;
  height: 200px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.image-preview :deep(.el-image) {
  width: 200px;
  height: 200px;
  display: block;
}

.image-preview:hover .image-mask {
  opacity: 1;
}

.image-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  opacity: 0;
  transition: opacity 0.2s;
}

.image-mask-x {
  color: #fff;
  font-size: 48px;
  font-weight: 300;
  line-height: 1;
}

.image-placeholder {
  width: 200px;
  height: 200px;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.2s;
}

.image-placeholder:hover {
  border-color: #1677ff;
}

.image-placeholder-plus {
  font-size: 36px;
  color: #bbb;
  line-height: 1;
}

.image-placeholder-text {
  margin-top: 8px;
  color: #999;
  font-size: 0.85rem;
}
</style>
