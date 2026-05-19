<template>
  <div class="all-keys animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">密钥管理</h1>
        <p class="page-subtitle">管理所有用户的 API Keys</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="filter-bar glass-card">
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 130px" @change="fetchKeys">
        <el-option label="活跃" value="active" />
        <el-option label="暂停" value="suspended" />
        <el-option label="已撤销" value="revoked" />
      </el-select>
      <div class="search-total">共 {{ total }} 个 Key</div>
    </div>

    <div class="glass-card">
      <el-table :data="keys" v-loading="loading" empty-text="暂无数据">
        <el-table-column label="名称" min-width="130">
          <template #default="{ row }">
            <span class="key-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Key 值" width="220">
          <template #default="{ row }">
            <div style="display:flex; align-items:center; gap:8px;">
              <code class="key-prefix-code">
                {{ showKeyMap[row.id] ? (row.plaintext_key ? row.plaintext_key.slice(0, 10) + '...' : row.key_prefix + '...') : (row.key_prefix + '••••') }}
              </code>
              <el-button
                v-if="row.plaintext_key"
                size="small"
                circle
                style="margin-left: 4px;"
                @click="toggleKeyVisibility(row.id)"
              >
                <el-icon><View v-if="!showKeyMap[row.id]" /><Hide v-else /></el-icon>
              </el-button>
              <el-button
                v-if="row.plaintext_key"
                size="small"
                circle
                style="margin-left: 4px;"
                @click="copyKeyText(row.plaintext_key)"
              >
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="RPM 限制" width="110">
          <template #default="{ row }">
            <span class="meta-text">{{ row.rate_limit_rpm === 0 ? '无限' : row.rate_limit_rpm }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日 Token 限额" width="130">
          <template #default="{ row }">
            <span class="meta-text">{{ row.token_limit_daily === 0 ? '无限' : formatNum(row.token_limit_daily) }}</span>
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
        <el-table-column label="累计使用" width="110">
          <template #default="{ row }">
            <span class="meta-text">{{ formatNum(row.total_tokens_used) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">
            <span class="meta-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="到期时间" width="150">
          <template #default="{ row }">
            <span class="meta-text">{{ row.expires_at ? formatDate(row.expires_at) : '永久有效' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              :type="row.status === 'active' ? 'warning' : 'success'"
              size="small"
              @click="toggleKeyStatus(row)"
              v-if="row.status !== 'revoked'"
            >
              {{ row.status === 'active' ? '暂停' : '激活' }}
            </el-button>
            <el-button type="danger" size="small" @click="revokeKey(row)">删除</el-button>
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

    <!-- Edit Dialog -->
    <el-dialog v-model="showEditDialog" title="编辑 Key 配置" width="420px">
      <el-form :model="editForm" label-width="110px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="RPM 限制">
          <el-input-number v-model="editForm.rate_limit_rpm" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="日 Token 限额">
          <el-input-number v-model="editForm.token_limit_daily" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="允许模型">
          <el-select
            v-model="editForm.allowed_models"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="留空表示允许全部模型 (输入按回车添加)"
            style="width: 100%"
          >
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveKey">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { View, Hide, CopyDocument } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import type { APIKey } from '@/types'
import dayjs from 'dayjs'

const keys = ref<APIKey[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const statusFilter = ref<string | null>(null)
const showEditDialog = ref(false)
const saving = ref(false)
const selectedKey = ref<APIKey | null>(null)
const editForm = reactive({ name: '', rate_limit_rpm: 60, token_limit_daily: 0, allowed_models: [] as string[] })

const showKeyMap = ref<Record<string, boolean>>({})

function toggleKeyVisibility(id: string) {
  showKeyMap.value[id] = !showKeyMap.value[id]
}

async function copyKeyText(text: string) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = text
      textArea.style.position = "fixed"
      textArea.style.left = "-999999px"
      textArea.style.top = "-999999px"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      textArea.remove()
      if (!successful) throw new Error('Fallback copy failed')
    }
    ElMessage.success('已复制密钥到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

function statusTag(s: string) { return { active: 'success', suspended: 'warning', revoked: 'danger' }[s] || 'info' }
function statusLabel(s: string) { return { active: '活跃', suspended: '暂停', revoked: '已撤销' }[s] || s }
function formatNum(n: number) { return n >= 1000 ? (n / 1000).toFixed(1) + 'K' : n.toString() }
function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }

async function fetchKeys() {
  loading.value = true
  try {
    const res = await adminApi.listAllKeys({
      skip: (page.value - 1) * pageSize,
      limit: pageSize,
      status: statusFilter.value ?? undefined,
    })
    keys.value = res.data.items
    total.value = res.data.total
  } finally { loading.value = false }
}

function openEdit(key: APIKey) {
  selectedKey.value = key
  editForm.name = key.name
  editForm.rate_limit_rpm = key.rate_limit_rpm
  editForm.token_limit_daily = key.token_limit_daily
  editForm.allowed_models = [...(key.allowed_models || [])]
  showEditDialog.value = true
}

async function saveKey() {
  if (!selectedKey.value) return
  saving.value = true
  try {
    await adminApi.updateKey(selectedKey.value.id, { ...editForm })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    fetchKeys()
  } finally { saving.value = false }
}

async function toggleKeyStatus(key: APIKey) {
  const newStatus = key.status === 'active' ? 'suspended' : 'active'
  await adminApi.updateKey(key.id, { status: newStatus })
  ElMessage.success(newStatus === 'active' ? 'Key 已激活' : 'Key 已暂停')
  fetchKeys()
}

async function revokeKey(key: APIKey) {
  await ElMessageBox.confirm(`确定要删除 "${key.name}" 吗？删除后无法恢复。`, '确认删除', { type: 'warning' })
  await adminApi.deleteKey(key.id)
  ElMessage.success('Key 已删除')
  fetchKeys()
}

onMounted(fetchKeys)
</script>

<style scoped>
.filter-bar { padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.search-total { font-size: 13px; color: var(--color-text-secondary); }
.table-footer { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border); }
.key-name { font-weight: 500; color: var(--color-text-primary); }
.key-prefix-code { font-family: monospace; font-size: 13px; color: var(--color-primary-light); background: rgba(99,102,241,0.1); padding: 3px 8px; border-radius: 6px; display: inline-block; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle; }
.meta-text { font-size: 13px; color: var(--color-text-secondary); }
</style>
