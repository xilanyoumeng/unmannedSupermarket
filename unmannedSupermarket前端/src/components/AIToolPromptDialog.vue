<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useAssistantStore, type ToolCallAction, type ToolAckPayload } from '../stores/assistant'

type PromptValue = string | number | boolean | null

interface PromptOption {
  label: string
  value: PromptValue
}

interface PromptField {
  name: string
  label: string
  type?: 'text' | 'number' | 'textarea' | 'select'
  required?: boolean
  placeholder?: string
  default?: PromptValue
  options?: PromptOption[]
}

interface PromptPayload {
  title?: string
  message?: string
  mode?: 'confirm' | 'select' | 'form'
  options?: PromptOption[]
  fields?: PromptField[]
  allowCustomInput?: boolean
  customInputLabel?: string
  customInputPlaceholder?: string
  confirmText?: string
  cancelText?: string
}

const store = useAssistantStore()
const CUSTOM_OPTION_VALUE = '__ai_custom_input__'
const selectedValue = ref<PromptValue>(null)
const customInput = ref('')
const formValues = reactive<Record<string, any>>({})
const formError = ref('')

const action = computed<ToolCallAction | null>(() => {
  return store.pendingAction?.type === 'ask_user' ? store.pendingAction : null
})

const payload = computed<PromptPayload>(() => {
  const raw = action.value?.payload
  if (raw && typeof raw === 'object') return raw as PromptPayload
  return {}
})

const mode = computed(() => {
  if (payload.value.mode) return payload.value.mode
  if (payload.value.fields?.length) return 'form'
  if (payload.value.options?.length) return 'select'
  return 'confirm'
})

const title = computed(() => payload.value.title || action.value?.label || '需要确认')
const message = computed(() => payload.value.message || 'AI 导购需要您确认后继续执行。')
const confirmText = computed(() => payload.value.confirmText || '确认并继续')
const cancelText = computed(() => payload.value.cancelText || '取消')
const allowCustomInput = computed(() => {
  return mode.value === 'select' && !!payload.value.options?.length && payload.value.allowCustomInput !== false
})
const customInputLabel = computed(() => payload.value.customInputLabel || '其他商品')
const customInputPlaceholder = computed(() => {
  return payload.value.customInputPlaceholder || '或者您想要其他商品，也可以输入，我帮您查找哦'
})

watch(action, () => {
  formError.value = ''
  selectedValue.value = null
  customInput.value = ''
  Object.keys(formValues).forEach((key) => delete formValues[key])

  const fields = payload.value.fields || []
  fields.forEach((field) => {
    formValues[field.name] = field.default ?? (field.type === 'number' ? 1 : '')
  })
}, { immediate: true })

function validateForm() {
  const fields = payload.value.fields || []
  for (const field of fields) {
    const value = formValues[field.name]
    if (field.required && (value === '' || value === null || value === undefined)) {
      formError.value = `请填写${field.label}`
      return false
    }
  }
  return true
}

function submit() {
  if (!action.value) return
  formError.value = ''

  let data: ToolAckPayload = { confirmed: true }
  if (mode.value === 'select') {
    if (selectedValue.value === null || selectedValue.value === undefined || selectedValue.value === '') {
      formError.value = '请选择一个选项'
      return
    }
    if (selectedValue.value === CUSTOM_OPTION_VALUE) {
      const customText = customInput.value.trim()
      if (!customText) {
        formError.value = `请输入${customInputLabel.value}`
        return
      }
      data = {
        selected: CUSTOM_OPTION_VALUE,
        option: { label: customInputLabel.value, value: CUSTOM_OPTION_VALUE },
        isCustom: true,
        customInput: customText,
        values: { query: customText },
      }
      store.completePendingAction(action.value, true, data)
      return
    }
    const selected = payload.value.options?.find((option) => option.value === selectedValue.value)
    data = { selected: selectedValue.value, option: selected }
  } else if (mode.value === 'form') {
    if (!validateForm()) return
    data = { values: { ...formValues } }
  }

  store.completePendingAction(action.value, true, data)
}

function cancel() {
  if (!action.value) return
  store.completePendingAction(action.value, false, { cancelled: true })
}
</script>

<template>
  <el-dialog
    :model-value="!!action"
    :title="title"
    width="420px"
    append-to-body
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="ai-tool-dialog"
  >
    <p class="ai-tool-message">{{ message }}</p>

    <el-radio-group
      v-if="mode === 'select'"
      v-model="selectedValue"
      class="ai-tool-options"
    >
      <el-radio
        v-for="option in payload.options || []"
        :key="String(option.value)"
        :value="option.value"
        border
      >
        {{ option.label }}
      </el-radio>
      <el-radio
        v-if="allowCustomInput"
        :value="CUSTOM_OPTION_VALUE"
        border
      >
        {{ customInputLabel }}
      </el-radio>
    </el-radio-group>

    <el-input
      v-if="mode === 'select' && allowCustomInput && selectedValue === CUSTOM_OPTION_VALUE"
      v-model="customInput"
      class="ai-tool-custom-input"
      :placeholder="customInputPlaceholder"
      clearable
      @keydown.enter.prevent="submit"
    />

    <el-form v-else-if="mode === 'form'" label-position="top" class="ai-tool-form">
      <el-form-item
        v-for="field in payload.fields || []"
        :key="field.name"
        :label="field.label"
        :required="field.required"
      >
        <el-input-number
          v-if="field.type === 'number'"
          v-model="formValues[field.name]"
          :min="1"
          controls-position="right"
          style="width: 100%"
        />
        <el-select
          v-else-if="field.type === 'select'"
          v-model="formValues[field.name]"
          :placeholder="field.placeholder || '请选择'"
          style="width: 100%"
        >
          <el-option
            v-for="option in field.options || []"
            :key="String(option.value)"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-input
          v-else
          v-model="formValues[field.name]"
          :type="field.type === 'textarea' ? 'textarea' : 'text'"
          :rows="field.type === 'textarea' ? 3 : undefined"
          :placeholder="field.placeholder"
        />
      </el-form-item>
    </el-form>

    <div v-if="formError" class="ai-tool-error">{{ formError }}</div>

    <template #footer>
      <el-button @click="cancel">{{ cancelText }}</el-button>
      <el-button type="primary" @click="submit">{{ confirmText }}</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.ai-tool-message {
  margin: 0 0 16px;
  color: #475569;
  line-height: 1.6;
  white-space: pre-line;
}

.ai-tool-options {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  width: 100%;
}

.ai-tool-options :deep(.el-radio) {
  margin-right: 0;
}

.ai-tool-custom-input {
  margin-top: 12px;
}

.ai-tool-form {
  margin-top: 4px;
}

.ai-tool-error {
  color: #d93025;
  font-size: 0.82rem;
  margin-top: 8px;
}
</style>
