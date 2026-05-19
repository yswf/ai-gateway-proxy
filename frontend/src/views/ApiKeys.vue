<template>
  <div class="api-keys-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">API Keys</h1>
        <p class="page-subtitle">管理您的 API 访问密钥</p>
      </div>
    </div>

    <!-- Key List -->
    <div class="glass-card keys-table-card">
      <el-table
        :data="keys"
        v-loading="loading"
        empty-text="暂无 API Key，请前往“申请管理”模块提交数据源访问申请"
        row-class-name="key-row"
      >
        <el-table-column label="名称" min-width="140">
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

        <el-table-column label="到期时间" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ row.expires_at ? formatDate(row.expires_at) : '永久有效' }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, View, Hide } from '@element-plus/icons-vue'
import { apiKeysApi } from '@/api/apiKeys'
import type { APIKey } from '@/types'
import dayjs from 'dayjs'

const keys = ref<APIKey[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

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
    ElMessage.error('复制失败，请手动选择复制')
  }
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



onMounted(async () => {
  await fetchKeys()
})
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
