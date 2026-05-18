<template>
  <div class="models-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">模型管理</h1>
        <p class="page-subtitle">管理系统中可用的 AI 模型列表</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate" id="btn-add-model">
        添加模型
      </el-button>
    </div>

    <!-- Stats bar -->
    <div class="model-stats">
      <div class="model-stat-item">
        <span class="stat-num">{{ models.length }}</span>
        <span class="stat-lbl">全部模型</span>
      </div>
      <div class="model-stat-item">
        <span class="stat-num" style="color: var(--color-success)">{{ enabledCount }}</span>
        <span class="stat-lbl">已启用</span>
      </div>
      <div class="model-stat-item">
        <span class="stat-num" style="color: var(--color-text-muted)">{{ disabledCount }}</span>
        <span class="stat-lbl">已禁用</span>
      </div>
    </div>

    <!-- Table -->
    <div class="table-card">
      <div class="table-toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索模型名称..."
          :prefix-icon="Search"
          clearable
          style="max-width: 280px"
        />
        <div style="display:flex;gap:8px;align-items:center;">
          <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 110px">
            <el-option label="已启用" :value="true" />
            <el-option label="已禁用" :value="false" />
          </el-select>
        </div>
      </div>

      <el-table
        :data="filteredModels"
        v-loading="loading"
        empty-text="暂无模型，点击右上角添加"
        row-key="id"
        stripe
      >
        <el-table-column label="排序" width="70" align="center">
          <template #default="{ row }">
            <span class="sort-num">{{ row.sort_order }}</span>
          </template>
        </el-table-column>

        <el-table-column label="模型 ID" min-width="180">
          <template #default="{ row }">
            <code class="key-badge">{{ row.name }}</code>
          </template>
        </el-table-column>

        <el-table-column label="数据源 (Provider)" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="meta-text" v-if="row.provider_id">{{ getProviderName(row.provider_id) }}</span>
            <span class="meta-text" v-else style="color:var(--color-text-muted)">无 (全局)</span>
          </template>
        </el-table-column>

        <el-table-column label="显示名称" min-width="160">
          <template #default="{ row }">
            <span class="model-display-name">{{ row.display_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="说明" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="上下文长度" width="120" align="right">
          <template #default="{ row }">
            <span class="meta-text">{{ row.context_window ? fmt(row.context_window) : '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="最大输出" width="110" align="right">
          <template #default="{ row }">
            <span class="meta-text">{{ row.max_tokens ? fmt(row.max_tokens) : '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_enabled"
              :loading="togglingId === row.id"
              @change="(val: boolean) => toggleModel(row, val)"
              active-color="#9ab856"
            />
          </template>
        </el-table-column>

        <el-table-column label="添加时间" width="150">
          <template #default="{ row }">
            <span class="meta-text">{{ dayjs(row.created_at).format('YYYY-MM-DD') }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteModel(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="showDialog"
      :title="editingModel ? '编辑模型' : '添加模型'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="模型 ID" prop="name">
          <el-input
            v-model="form.name"
            placeholder="例如: gpt-4o"
            :disabled="!!editingModel"
            id="input-model-name"
          />
          <div class="form-hint">唯一标识符，与 OpenAI API 中的 model 字段一致</div>
        </el-form-item>
        <el-form-item label="归属数据源">
          <el-select v-model="form.provider_id" placeholder="选择归属数据源（可选）" clearable style="width: 100%">
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.display_name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="例如: GPT-4o" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="模型描述（可选）"
          />
        </el-form-item>
        <el-form-item label="上下文窗口">
          <el-input-number v-model="form.context_window" :min="0" style="width:100%" placeholder="如: 128000" />
          <div class="form-hint">模型最大上下文 token 数，0 表示未知</div>
        </el-form-item>
        <el-form-item label="最大输出">
          <el-input-number v-model="form.max_tokens" :min="0" style="width:100%" placeholder="如: 16384" />
          <div class="form-hint">单次请求最大输出 token 数，0 表示未限制</div>
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" style="width:100%" />
          <div class="form-hint">数值越小越靠前</div>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_enabled" active-color="#9ab856" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveModel" id="btn-save-model">
          {{ editingModel ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import dayjs from 'dayjs'
import { adminApi } from '@/api/admin'
import type { AIModel, Provider } from '@/types'

const models = ref<AIModel[]>([])
const providers = ref<Provider[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editingModel = ref<AIModel | null>(null)
const togglingId = ref<string | null>(null)
const keyword = ref('')
const filterStatus = ref<boolean | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  provider_id: null as string | null,
  name: '',
  display_name: '',
  description: '',
  is_enabled: true,
  max_tokens: 0,
  context_window: 0,
  sort_order: 0,
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入模型 ID', trigger: 'blur' },
    { pattern: /^[\w./:+-]+$/, message: '只允许字母、数字、点、连字符、斜杠等', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
}

function fmt(n: number) {
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K'
  return n.toString()
}

const enabledCount = computed(() => models.value.filter(m => m.is_enabled).length)
const disabledCount = computed(() => models.value.filter(m => !m.is_enabled).length)

const filteredModels = computed(() => {
  return models.value.filter(m => {
    const kw = keyword.value.toLowerCase()
    const matchKw = !kw || m.name.toLowerCase().includes(kw) || m.display_name.toLowerCase().includes(kw)
    const matchStatus = filterStatus.value === null || m.is_enabled === filterStatus.value
    return matchKw && matchStatus
  })
})

function getProviderName(id: string) {
  const p = providers.value.find(p => p.id === id)
  return p ? p.display_name : id
}

async function fetchProviders() {
  try {
    const res = await adminApi.listProviders({ limit: 1000 })
    providers.value = res.data.items
  } catch (e) {
    // ignore
  }
}

async function fetchModels() {
  loading.value = true
  try {
    const res = await adminApi.listModels({ limit: 1000 })
    models.value = res.data.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingModel.value = null
  Object.assign(form, { provider_id: null, name: '', display_name: '', description: '', is_enabled: true, max_tokens: 0, context_window: 0, sort_order: 0 })
  showDialog.value = true
}

function openEdit(model: AIModel) {
  editingModel.value = model
  Object.assign(form, {
    provider_id: model.provider_id || null,
    name: model.name,
    display_name: model.display_name,
    description: model.description || '',
    is_enabled: model.is_enabled,
    max_tokens: model.max_tokens ?? 0,
    context_window: model.context_window ?? 0,
    sort_order: model.sort_order,
  })
  showDialog.value = true
}

async function saveModel() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingModel.value) {
      await adminApi.updateModel(editingModel.value.id, {
        provider_id: form.provider_id || null,
        display_name: form.display_name,
        description: form.description || null,
        is_enabled: form.is_enabled,
        max_tokens: form.max_tokens || null,
        context_window: form.context_window || null,
        sort_order: form.sort_order,
      })
      ElMessage.success('模型已更新')
    } else {
      await adminApi.createModel({
        provider_id: form.provider_id || null,
        name: form.name,
        display_name: form.display_name,
        description: form.description || null,
        is_enabled: form.is_enabled,
        max_tokens: form.max_tokens || null,
        context_window: form.context_window || null,
        sort_order: form.sort_order,
      })
      ElMessage.success('模型已添加')
    }
    showDialog.value = false
    await fetchModels()
  } finally {
    saving.value = false
  }
}

async function toggleModel(model: AIModel, enabled: boolean) {
  togglingId.value = String(model.id)
  try {
    await adminApi.updateModel(model.id, { is_enabled: enabled })
    model.is_enabled = enabled
    ElMessage.success(enabled ? '模型已启用' : '模型已禁用')
  } finally {
    togglingId.value = null
  }
}

async function deleteModel(model: AIModel) {
  await ElMessageBox.confirm(
    `确定要删除模型 "${model.display_name}" 吗？`,
    '确认删除',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await adminApi.deleteModel(model.id)
  ElMessage.success('模型已删除')
  await fetchModels()
}

onMounted(async () => {
  await fetchProviders()
  await fetchModels()
})
</script>

<style scoped>
.model-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px 24px;
  box-shadow: var(--shadow-sm);
}

.model-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 60px;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.stat-lbl {
  font-size: 12px;
  color: var(--color-text-muted);
}

.model-display-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.desc-text {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.meta-text {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.sort-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg-subtle);
  border-radius: 6px;
  padding: 2px 8px;
}

.form-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .model-stats { gap: 16px; }
}
</style>
