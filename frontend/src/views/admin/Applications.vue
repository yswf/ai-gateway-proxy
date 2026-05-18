<template>
  <div class="admin-apps-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">申请审批</h1>
        <p class="page-subtitle">处理用户的 API 数据源访问申请</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="table-card" style="margin-bottom: 20px; padding: 16px;">
      <el-radio-group v-model="filterStatus" @change="fetchApplications">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待审批</el-radio-button>
        <el-radio-button label="approved">已批准</el-radio-button>
        <el-radio-button label="rejected">已拒绝</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Table -->
    <div class="table-card">
      <el-table :data="applications" v-loading="loading" empty-text="暂无申请记录" stripe>
        <el-table-column label="申请时间" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ dayjs(row.created_at).format('YYYY-MM-DD HH:mm') }}</span>
          </template>
        </el-table-column>

        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">
            <div style="display:flex; flex-direction:column;">
              <span style="font-weight:600; color:var(--color-text-primary)">
                {{ row.user_display_name || row.user_email }}
              </span>
              <span class="meta-text" style="font-size: 12px">{{ row.user_email }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="目标数据源" min-width="150">
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

        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              type="primary"
              size="small"
              @click="openReview(row)"
            >
              审批
            </el-button>
            <el-button
              v-else
              type="info"
              size="small"
              @click="openReview(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Review Dialog -->
    <el-dialog
      v-model="showReviewDialog"
      :title="currentApp?.status === 'pending' ? '审批申请' : '申请详情'"
      width="500px"
    >
      <div v-if="currentApp" class="review-details">
        <div class="detail-row">
          <span class="lbl">申请人</span>
          <span class="val">{{ currentApp.user_display_name }} ({{ currentApp.user_email }})</span>
        </div>
        <div class="detail-row">
          <span class="lbl">数据源</span>
          <span class="val">{{ currentApp.provider_display_name }}</span>
        </div>
        <div class="detail-row">
          <span class="lbl">申请模型</span>
          <span class="val">
            <template v-if="!currentApp.requested_models || currentApp.requested_models.length === 0">全部模型 (无限制)</template>
            <template v-else>
              <el-tag v-for="m in currentApp.requested_models" :key="m" size="small" type="info" style="margin-right: 4px; margin-bottom: 4px;">{{ m }}</el-tag>
            </template>
          </span>
        </div>
        <div class="detail-row">
          <span class="lbl">申请时间</span>
          <span class="val">{{ dayjs(currentApp.created_at).format('YYYY-MM-DD HH:mm:ss') }}</span>
        </div>
        <div class="detail-row">
          <span class="lbl">申请理由</span>
          <div class="val text-block">{{ currentApp.reason }}</div>
        </div>

        <template v-if="currentApp.status === 'pending'">
          <el-divider />
          <el-form label-position="top">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 8px;">
              <el-form-item label="速率限制 (RPM)">
                <el-input-number v-model="rateLimit" :min="0" style="width: 100%" />
                <div style="font-size: 11px; color: var(--color-text-secondary); margin-top: 4px;">每分钟最大请求数，0表示无限制</div>
              </el-form-item>
              <el-form-item label="日 Token 限额">
                <el-input-number v-model="tokenLimit" :min="0" style="width: 100%" />
                <div style="font-size: 11px; color: var(--color-text-secondary); margin-top: 4px;">每日最大Token限额，0表示无限制</div>
              </el-form-item>
            </div>
            <el-form-item label="到期时间">
              <el-date-picker
                v-model="expiresAt"
                type="datetime"
                placeholder="留空则永久有效"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="管理员回复 (可选)">
              <el-input
                v-model="reviewNote"
                type="textarea"
                :rows="2"
                placeholder="填写给用户的回复，如拒绝原因或分配说明"
              />
            </el-form-item>
          </el-form>
        </template>
        
        <template v-else>
          <el-divider />
          <div class="detail-row">
            <span class="lbl">审批结果</span>
            <span class="val">
              <el-tag :type="currentApp.status === 'approved' ? 'success' : 'danger'" size="small">
                {{ currentApp.status === 'approved' ? '已批准' : '已拒绝' }}
              </el-tag>
            </span>
          </div>
          <div class="detail-row">
            <span class="lbl">审批回复</span>
            <div class="val text-block">{{ currentApp.admin_note || '无' }}</div>
          </div>
          <div class="detail-row">
            <span class="lbl">审批时间</span>
            <span class="val">{{ currentApp.reviewed_at ? dayjs(currentApp.reviewed_at).format('YYYY-MM-DD HH:mm:ss') : '-' }}</span>
          </div>
        </template>
      </div>

      <template #footer v-if="currentApp?.status === 'pending'">
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="danger" :loading="processing" @click="submitReview('rejected')">拒绝</el-button>
        <el-button type="success" :loading="processing" @click="submitReview('approved')">批准 (并生成 Key)</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { adminApi } from '@/api/admin'
import type { KeyApplication } from '@/types'

const applications = ref<KeyApplication[]>([])
const loading = ref(false)
const filterStatus = ref<string>('pending')

const showReviewDialog = ref(false)
const currentApp = ref<KeyApplication | null>(null)
const reviewNote = ref('')
const processing = ref(false)

const rateLimit = ref(60)
const tokenLimit = ref(0)
const expiresAt = ref<any>(null)

async function fetchApplications() {
  loading.value = true
  try {
    const params: any = { limit: 100 }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    const res = await adminApi.listApplications(params)
    applications.value = res.data.items
  } finally {
    loading.value = false
  }
}

function openReview(app: KeyApplication) {
  currentApp.value = app
  reviewNote.value = ''
  rateLimit.value = 60
  tokenLimit.value = 0
  expiresAt.value = null
  showReviewDialog.value = true
}

async function submitReview(status: 'approved' | 'rejected') {
  if (!currentApp.value) return
  processing.value = true
  try {
    await adminApi.reviewApplication(currentApp.value.id, {
      status,
      admin_note: reviewNote.value || undefined,
      rate_limit_rpm: status === 'approved' ? rateLimit.value : undefined,
      token_limit_daily: status === 'approved' ? tokenLimit.value : undefined,
      expires_at: (status === 'approved' && expiresAt.value) ? expiresAt.value.toISOString() : undefined,
    })
    ElMessage.success(status === 'approved' ? '申请已批准，API Key 已生成' : '申请已拒绝')
    showReviewDialog.value = false
    await fetchApplications()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    processing.value = false
  }
}

onMounted(() => {
  fetchApplications()
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

.review-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lbl {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
}

.val {
  font-size: 14px;
  color: var(--color-text-primary);
}

.text-block {
  background: var(--color-bg-subtle);
  padding: 10px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
