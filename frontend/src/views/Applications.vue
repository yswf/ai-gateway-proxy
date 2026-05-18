<template>
  <div class="user-applications-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的申请</h1>
        <p class="page-subtitle">申请新的 API 数据源访问权限</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openApply">申请新权限</el-button>
    </div>

    <!-- Applications Table -->
    <div class="table-card">
      <el-table :data="applications" v-loading="loading" empty-text="暂无申请记录" stripe>
        <el-table-column label="申请时间" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ dayjs(row.created_at).format('YYYY-MM-DD HH:mm') }}</span>
          </template>
        </el-table-column>

        <el-table-column label="数据源" min-width="150">
          <template #default="{ row }">
            <span style="font-weight: 500; color: var(--color-text-primary)">
              {{ row.provider_display_name || row.provider_name }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="申请模型" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="!row.requested_models || row.requested_models.length === 0" class="meta-text">全部模型</span>
            <span v-else>
              <el-tag v-for="m in row.requested_models" :key="m" size="small" type="info" style="margin:2px">{{ m }}</el-tag>
            </span>
          </template>
        </el-table-column>

        <el-table-column label="申请理由" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="desc-text">{{ row.reason }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning" size="small">待审批</el-tag>
            <el-tag v-else-if="row.status === 'approved'" type="success" size="small">已批准</el-tag>
            <el-tag v-else-if="row.status === 'rejected'" type="danger" size="small">已拒绝</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="管理员回复" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="meta-text">{{ row.admin_note || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="danger"
              size="small"
              @click="withdrawApp(row)"
            >
              撤回
            </el-button>
            <span v-else class="meta-text" style="font-size: 12px">不可操作</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Apply Dialog -->
    <el-dialog v-model="showApplyDialog" title="申请数据源权限" width="500px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="top">
        <el-form-item label="选择数据源" prop="provider_id">
          <el-select v-model="form.provider_id" placeholder="请选择您需要访问的数据源" style="width: 100%" @change="onProviderChange">
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.display_name"
              :value="p.id"
            >
              <div style="display:flex; justify-content:space-between;">
                <span>{{ p.display_name }}</span>
                <span style="color:var(--color-text-muted); font-size: 12px;">{{ p.name }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="选择模型 (可选)" prop="requested_models">
          <el-select
            v-model="form.requested_models"
            multiple
            placeholder="不选择则默认申请该源下所有模型"
            style="width: 100%"
            :disabled="!form.provider_id"
            :loading="fetchingModels"
          >
            <el-option
              v-for="m in availableModels"
              :key="m.name"
              :label="m.display_name"
              :value="m.name"
            >
              <div style="display:flex; justify-content:space-between;">
                <span>{{ m.display_name }}</span>
                <span style="color:var(--color-text-muted); font-size: 12px;">{{ m.name }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="申请理由" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="3"
            placeholder="请简要说明您的使用场景和需求..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApplyDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitApply">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import dayjs from 'dayjs'
import { applicationsApi } from '@/api/applications'
import type { KeyApplication, ProviderPublic, AIModel } from '@/types'

const applications = ref<KeyApplication[]>([])
const loading = ref(false)
const showApplyDialog = ref(false)
const submitting = ref(false)
const providers = ref<ProviderPublic[]>([])
const availableModels = ref<AIModel[]>([])
const fetchingModels = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  provider_id: '',
  requested_models: [] as string[],
  reason: '',
})

const rules: FormRules = {
  provider_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  reason: [{ required: true, message: '请填写申请理由', trigger: 'blur' }],
}

async function fetchApplications() {
  loading.value = true
  try {
    const res = await applicationsApi.myApplications({ limit: 100 })
    applications.value = res.data.items
  } finally {
    loading.value = false
  }
}

async function fetchProviders() {
  try {
    const res = await applicationsApi.listProviders()
    providers.value = res.data.items
  } catch (e) {
    // ignore
  }
}

async function onProviderChange(val: string) {
  form.requested_models = []
  if (!val) {
    availableModels.value = []
    return
  }
  fetchingModels.value = true
  try {
    const res = await applicationsApi.listModelsByProvider(val)
    availableModels.value = res.data.items
  } catch (e) {
    // ignore
  } finally {
    fetchingModels.value = false
  }
}

function openApply() {
  if (providers.value.length === 0) {
    fetchProviders()
  }
  form.provider_id = ''
  form.requested_models = []
  availableModels.value = []
  form.reason = ''
  showApplyDialog.value = true
}

async function submitApply() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    await applicationsApi.submit({
      provider_id: form.provider_id,
      requested_models: form.requested_models,
      reason: form.reason,
    })
    ElMessage.success('申请已提交，请等待管理员审批')
    showApplyDialog.value = false
    await fetchApplications()
  } catch (e: any) {
    if (e.response?.status === 409) {
      ElMessage.error('您已经有针对此数据源的待审批申请')
    } else {
      ElMessage.error('提交失败')
    }
  } finally {
    submitting.value = false
  }
}

async function withdrawApp(app: KeyApplication) {
  await ElMessageBox.confirm('确定撤回此申请吗？', '提示', { type: 'warning' })
  try {
    await applicationsApi.withdraw(app.id)
    ElMessage.success('已撤回申请')
    await fetchApplications()
  } catch (e) {
    ElMessage.error('撤回失败')
  }
}

onMounted(() => {
  fetchApplications()
  fetchProviders()
})
</script>

<style scoped>
.meta-text {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.desc-text {
  font-size: 13px;
  color: var(--color-text-primary);
}
</style>
