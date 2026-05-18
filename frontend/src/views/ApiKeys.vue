<template>
  <div class="api-keys-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">API Keys</h1>
        <p class="page-subtitle">管理您的 API 访问密钥</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true" id="create-key-btn">
        创建新 Key
      </el-button>
    </div>

    <!-- Key List -->
    <div class="glass-card keys-table-card">
      <el-table
        :data="keys"
        v-loading="loading"
        empty-text="暂无 API Key，点击右上角创建"
        row-class-name="key-row"
      >
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">
            <span class="key-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Key 前缀" width="160">
          <template #default="{ row }">
            <code class="key-prefix-code">{{ row.key_prefix }}••••••••</code>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="速率限制" width="120">
          <template #default="{ row }">
            <span class="meta-text">
              {{ row.rate_limit_rpm === 0 ? '无限制' : `${row.rate_limit_rpm} RPM` }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="日 Token 限额" width="140">
          <template #default="{ row }">
            <span class="meta-text">
              {{ row.token_limit_daily === 0 ? '无限制' : formatNumber(row.token_limit_daily) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="允许模型" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="!row.allowed_models || row.allowed_models.length === 0" class="meta-text">全部模型</span>
            <span v-else>
              <el-tag v-for="m in row.allowed_models" :key="m" size="small" type="info" style="margin:2px">{{ m }}</el-tag>
            </span>
          </template>
        </el-table-column>

        <el-table-column label="累计使用" width="120">
          <template #default="{ row }">
            <span class="meta-text">{{ formatNumber(row.total_tokens_used) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="最后使用" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ row.last_used_at ? formatDate(row.last_used_at) : '从未使用' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              size="small"
              :icon="Delete"
              @click="revokeKey(row)"
              :disabled="row.status === 'revoked'"
            >
              撤销
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchKeys"
          background
        />
      </div>
    </div>

    <!-- Create Key Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="创建新 API Key"
      width="480px"
      :close-on-click-modal="false"
      @close="resetCreateForm"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="110px">
        <el-form-item label="Key 名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：生产环境 Key" id="key-name-input" />
        </el-form-item>
        <el-form-item label="速率限制" prop="rate_limit_rpm">
          <el-input-number
            v-model="createForm.rate_limit_rpm"
            :min="0"
            :max="10000"
            style="width: 100%"
          />
          <div class="form-hint">每分钟最大请求数，0 表示无限制</div>
        </el-form-item>
        <el-form-item label="日 Token 限额" prop="token_limit_daily">
          <el-input-number
            v-model="createForm.token_limit_daily"
            :min="0"
            :max="100_000_000"
            style="width: 100%"
          />
          <div class="form-hint">每日最大 Token 用量，0 表示无限制</div>
        </el-form-item>
        <el-form-item label="允许模型">
          <el-select
            v-model="createForm.allowed_models"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="留空表示允许全部模型 (输入按回车添加)"
            style="width: 100%"
          >
          </el-select>
        </el-form-item>
        <el-form-item label="过期时间">
          <el-date-picker
            v-model="createForm.expires_at"
            type="datetime"
            placeholder="不设置则永久有效"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate" id="confirm-create-btn">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- Created Key Dialog (show full key once) -->
    <el-dialog
      v-model="showKeyDialog"
      title="🎉 Key 创建成功"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-alert
        title="请立即复制并安全保存，此密钥只显示一次！"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      />
      <div class="new-key-display">
        <code class="new-key-text">{{ newKey }}</code>
        <el-button :icon="CopyDocument" @click="copyKey" circle size="small" class="copy-btn" />
      </div>
      <template #footer>
        <el-button type="primary" @click="showKeyDialog = false; fetchKeys()">
          我已保存，关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, CopyDocument } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { apiKeysApi } from '@/api/apiKeys'
import type { APIKey } from '@/types'
import dayjs from 'dayjs'

const keys = ref<APIKey[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const showCreateDialog = ref(false)
const showKeyDialog = ref(false)
const creating = ref(false)
const newKey = ref('')
const createFormRef = ref<FormInstance>()

const createForm = reactive({
  name: '',
  rate_limit_rpm: 60,
  token_limit_daily: 0,
  expires_at: null as string | null,
  allowed_models: [] as string[],
})

const createRules: FormRules = {
  name: [{ required: true, message: '请输入 Key 名称', trigger: 'blur' }],
}

function statusTagType(status: string) {
  const map: Record<string, string> = { active: 'success', suspended: 'warning', revoked: 'danger' }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = { active: '活跃', suspended: '暂停', revoked: '已撤销' }
  return map[status] || status
}

function formatNumber(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return n.toString()
}

function formatDate(d: string) {
  return dayjs(d).format('YYYY-MM-DD HH:mm')
}

async function fetchKeys() {
  loading.value = true
  try {
    const res = await apiKeysApi.list({ skip: (page.value - 1) * pageSize, limit: pageSize })
    keys.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    const res = await apiKeysApi.create({
      name: createForm.name,
      rate_limit_rpm: createForm.rate_limit_rpm,
      token_limit_daily: createForm.token_limit_daily,
      expires_at: createForm.expires_at || null,
      allowed_models: createForm.allowed_models,
    })
    newKey.value = res.data.full_key
    showCreateDialog.value = false
    showKeyDialog.value = true
    ElMessage.success('Key 创建成功')
  } finally {
    creating.value = false
  }
}

async function revokeKey(key: APIKey) {
  await ElMessageBox.confirm(
    `确定要撤销 "${key.name}" 吗？撤销后无法恢复。`,
    '确认撤销',
    { type: 'warning', confirmButtonText: '确定撤销', cancelButtonText: '取消' }
  )
  await apiKeysApi.revoke(key.id)
  ElMessage.success('Key 已撤销')
  fetchKeys()
}

async function copyKey() {
  await navigator.clipboard.writeText(newKey.value)
  ElMessage.success('已复制到剪贴板')
}

function resetCreateForm() {
  createForm.name = ''
  createForm.rate_limit_rpm = 60
  createForm.token_limit_daily = 0
  createForm.expires_at = null
  createForm.allowed_models = []
}

onMounted(fetchKeys)
</script>

<style scoped>
.keys-table-card { padding: 0; overflow: hidden; }
.table-footer { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border); }
.key-name { font-weight: 500; color: var(--color-text-primary); }
.key-prefix-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--color-primary-light);
  background: rgba(99, 102, 241, 0.1);
  padding: 3px 8px;
  border-radius: 6px;
}
.meta-text { font-size: 13px; color: var(--color-text-secondary); }
.form-hint { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }
.new-key-display {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--radius-sm);
  padding: 16px;
}
.new-key-text {
  flex: 1;
  font-family: monospace;
  font-size: 13px;
  color: var(--color-primary-light);
  word-break: break-all;
}
.copy-btn { flex-shrink: 0; }
</style>
