<template>
  <div class="providers-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">API 源管理 (Providers)</h1>
        <p class="page-subtitle">管理不同的 OpenAI 兼容 API 数据源</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        添加数据源
      </el-button>
    </div>

    <!-- Table -->
    <div class="table-card">
      <el-table :data="providers" v-loading="loading" empty-text="暂无数据源" row-key="id" stripe>
        <el-table-column label="排序" width="70" align="center">
          <template #default="{ row }">
            <span class="sort-num">{{ row.sort_order }}</span>
          </template>
        </el-table-column>

        <el-table-column label="标识符 (ID)" min-width="120">
          <template #default="{ row }">
            <code class="key-badge">{{ row.name }}</code>
          </template>
        </el-table-column>

        <el-table-column label="显示名称" min-width="160">
          <template #default="{ row }">
            <span style="font-weight: 600; color: var(--color-text-primary)">{{ row.display_name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Base URL" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono text-muted">{{ row.base_url }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_enabled"
              :loading="togglingId === row.id"
              @change="(val: boolean) => toggleProvider(row, val)"
              active-color="#9ab856"
            />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteProvider(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="showDialog"
      :title="editingProvider ? '编辑数据源' : '添加数据源'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="标识符" prop="name">
          <el-input v-model="form.name" placeholder="如: azure-us-east" :disabled="!!editingProvider" />
          <div class="form-hint">唯一标识，不可重复</div>
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="如: 微软 Azure 美东区" />
        </el-form-item>
        <el-form-item label="Base URL" prop="base_url">
          <el-input v-model="form.base_url" placeholder="https://api.openai.com" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_enabled" active-color="#9ab856" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProvider">
          {{ editingProvider ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { adminApi } from '@/api/admin'
import type { Provider } from '@/types'

const providers = ref<Provider[]>([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editingProvider = ref<Provider | null>(null)
const togglingId = ref<string | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  display_name: '',
  base_url: '',
  api_key: '',
  description: '',
  is_enabled: true,
  sort_order: 0,
})

const rules: FormRules = {
  name: [{ required: true, message: '必填', trigger: 'blur' }],
  display_name: [{ required: true, message: '必填', trigger: 'blur' }],
  base_url: [{ required: true, message: '必填', trigger: 'blur' }],
  api_key: [{ required: true, message: '必填', trigger: 'blur' }],
}


async function fetchProviders() {
  loading.value = true
  try {
    const res = await adminApi.listProviders()
    providers.value = res.data.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingProvider.value = null
  Object.assign(form, { name: '', display_name: '', base_url: '', api_key: '', description: '', is_enabled: true, sort_order: 0 })
  showDialog.value = true
}

function openEdit(prov: Provider) {
  editingProvider.value = prov
  Object.assign(form, {
    name: prov.name,
    display_name: prov.display_name,
    base_url: prov.base_url,
    api_key: prov.api_key,
    description: prov.description || '',
    is_enabled: prov.is_enabled,
    sort_order: prov.sort_order,
  })
  showDialog.value = true
}

async function saveProvider() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingProvider.value) {
      await adminApi.updateProvider(editingProvider.value.id, {
        display_name: form.display_name,
        base_url: form.base_url,
        api_key: form.api_key,
        description: form.description || null,
        is_enabled: form.is_enabled,
        sort_order: form.sort_order,
      })
      ElMessage.success('已更新')
    } else {
      await adminApi.createProvider({
        name: form.name,
        display_name: form.display_name,
        base_url: form.base_url,
        api_key: form.api_key,
        description: form.description || null,
        is_enabled: form.is_enabled,
        sort_order: form.sort_order,
      })
      ElMessage.success('已添加')
    }
    showDialog.value = false
    await fetchProviders()
  } finally {
    saving.value = false
  }
}

async function toggleProvider(prov: Provider, enabled: boolean) {
  togglingId.value = prov.id
  try {
    await adminApi.updateProvider(prov.id, { is_enabled: enabled })
    prov.is_enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } finally {
    togglingId.value = null
  }
}

async function deleteProvider(prov: Provider) {
  await ElMessageBox.confirm('确定删除此数据源？相关模型和密钥可能会受到影响。', '警告', { type: 'warning' })
  await adminApi.deleteProvider(prov.id)
  ElMessage.success('已删除')
  await fetchProviders()
}


onMounted(fetchProviders)
</script>

<style scoped>
.sort-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg-subtle);
  border-radius: 6px;
  padding: 2px 8px;
}
.text-muted {
  color: var(--color-text-secondary);
}
.form-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
  margin-top: 4px;
}
</style>
