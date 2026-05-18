<template>
  <div class="admin-users animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">管理系统所有用户账号</p>
      </div>
    </div>

    <!-- Search -->
    <div class="search-bar glass-card">
      <el-input
        v-model="search"
        placeholder="搜索邮箱或姓名..."
        :prefix-icon="Search"
        clearable
        style="max-width: 320px"
        @input="debouncedSearch"
        id="user-search-input"
      />
      <div class="search-total">共 {{ total }} 位用户</div>
    </div>

    <!-- Table -->
    <div class="glass-card">
      <el-table :data="users" v-loading="loading" empty-text="暂无用户">
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar-sm">{{ (row.display_name || row.email).charAt(0).toUpperCase() }}</div>
              <div>
                <div class="user-name">{{ row.display_name || '-' }}</div>
                <div class="user-email">{{ row.email }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="用户名" width="130">
          <template #default="{ row }">
            <span class="meta-text">{{ row.username || '(OAuth)' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="注册时间" width="160">
          <template #default="{ row }">
            <span class="meta-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button
              :type="row.is_active ? 'danger' : 'success'"
              size="small"
              @click="toggleStatus(row)"
              :disabled="row.role === 'superadmin'"
            >
              {{ row.is_active ? '禁用' : '启用' }}
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
          @current-change="fetchUsers"
          background
        />
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="用户" value="user" />
            <el-option label="管理员" value="admin" />
            <el-option v-if="auth.isSuperAdmin" label="超级管理员" value="superadmin" />
          </el-select>
        </el-form-item>
        <el-form-item label="新密码" v-if="selectedUser?.username">
          <el-input v-model="editForm.password" type="password" show-password placeholder="留空不修改" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types'
import dayjs from 'dayjs'

const auth = useAuthStore()
const users = ref<User[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref('')
let searchTimer: ReturnType<typeof setTimeout>

const showEditDialog = ref(false)
const saving = ref(false)
const selectedUser = ref<User | null>(null)
const editForm = reactive({ display_name: '', role: 'user', password: '' })

function roleLabel(role: string) {
  const map: Record<string, string> = { superadmin: '超级管理员', admin: '管理员', user: '用户' }
  return map[role] || role
}

function roleTagType(role: string) {
  const map: Record<string, string> = { superadmin: 'danger', admin: 'warning', user: 'info' }
  return map[role] || 'info'
}

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; fetchUsers() }, 400)
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await adminApi.listUsers({
      skip: (page.value - 1) * pageSize,
      limit: pageSize,
      search: search.value || undefined,
    })
    users.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function openEditDialog(user: User) {
  selectedUser.value = user
  editForm.display_name = user.display_name || ''
  editForm.role = user.role
  editForm.password = ''
  showEditDialog.value = true
}

async function saveUser() {
  if (!selectedUser.value) return
  saving.value = true
  try {
    const payload: any = { display_name: editForm.display_name, role: editForm.role }
    if (editForm.password) payload.password = editForm.password
    await adminApi.updateUser(selectedUser.value.id, payload)
    ElMessage.success('用户信息已更新')
    showEditDialog.value = false
    fetchUsers()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(user: User) {
  await adminApi.updateUser(user.id, { is_active: !user.is_active })
  ElMessage.success(user.is_active ? '账号已禁用' : '账号已启用')
  fetchUsers()
}

onMounted(fetchUsers)
</script>

<style scoped>
.search-bar { padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.search-total { font-size: 13px; color: var(--color-text-secondary); }
.table-footer { padding: 16px 20px; display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border); }
.user-cell { display: flex; align-items: center; gap: 10px; }
.user-avatar-sm { width: 32px; height: 32px; background: var(--gradient-primary); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 13px; flex-shrink: 0; }
.user-name { font-size: 14px; font-weight: 500; color: var(--color-text-primary); }
.user-email { font-size: 12px; color: var(--color-text-muted); }
.meta-text { font-size: 13px; color: var(--color-text-secondary); }
</style>
