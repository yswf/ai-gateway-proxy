<template>
  <div class="profile-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人资料</h1>
        <p class="page-subtitle">管理您的账号信息</p>
      </div>
    </div>

    <div class="profile-layout">
      <!-- Avatar Card -->
      <div class="glass-card avatar-card">
        <div class="avatar-circle">{{ userInitial }}</div>
        <h3 class="avatar-name">{{ auth.user?.display_name || '用户' }}</h3>
        <p class="avatar-email">{{ auth.user?.email }}</p>
        <el-tag :type="roleTagType" style="margin-top: 12px">{{ roleLabel }}</el-tag>
      </div>

      <!-- Info Form -->
      <div class="glass-card info-card">
        <h3 class="card-section-title">账号信息</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="显示名称">
            {{ auth.user?.display_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            {{ auth.user?.email }}
          </el-descriptions-item>
          <el-descriptions-item label="用户名">
            {{ auth.user?.username || '(OAuth 账号)' }}
          </el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag :type="roleTagType" size="small">{{ roleLabel }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="账号状态">
            <el-tag type="success" size="small">正常</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- Change password (only for local accounts) -->
        <template v-if="auth.user?.username">
          <el-divider />
          <h3 class="card-section-title">修改密码</h3>
          <el-form ref="pwFormRef" :model="pwForm" :rules="pwRules" label-width="100px">
            <el-form-item label="新密码" prop="password">
              <el-input v-model="pwForm.password" type="password" show-password placeholder="请输入新密码" />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm">
              <el-input v-model="pwForm.confirm" type="password" show-password placeholder="再次输入新密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="pwLoading" @click="changePassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const pwFormRef = ref<FormInstance>()
const pwLoading = ref(false)

const pwForm = reactive({ password: '', confirm: '' })

const validateConfirm = (_: any, value: string, callback: Function) => {
  if (value !== pwForm.password) callback(new Error('两次密码不一致'))
  else callback()
}

const pwRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [{ validator: validateConfirm, trigger: 'blur' }],
}

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const map: Record<string, string> = { superadmin: '超级管理员', admin: '管理员', user: '用户' }
  return map[auth.user?.role ?? 'user'] || '用户'
})

const roleTagType = computed(() => {
  const map: Record<string, string> = { superadmin: 'danger', admin: 'warning', user: 'info' }
  return map[auth.user?.role ?? 'user'] || 'info'
})

async function changePassword() {
  if (!pwFormRef.value) return
  const valid = await pwFormRef.value.validate().catch(() => false)
  if (!valid || !auth.user) return
  pwLoading.value = true
  try {
    await adminApi.updateUser(auth.user.id, { password: pwForm.password })
    ElMessage.success('密码已更新')
    pwForm.password = ''
    pwForm.confirm = ''
  } finally {
    pwLoading.value = false
  }
}
</script>

<style scoped>
.profile-layout { display: grid; grid-template-columns: 260px 1fr; gap: 20px; }
@media (max-width: 768px) { .profile-layout { grid-template-columns: 1fr; } }
.avatar-card { padding: 32px 24px; display: flex; flex-direction: column; align-items: center; text-align: center; }
.avatar-circle { width: 80px; height: 80px; background: var(--gradient-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 700; color: white; margin-bottom: 16px; box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4); }
.avatar-name { font-size: 18px; font-weight: 600; color: var(--color-text-primary); }
.avatar-email { font-size: 13px; color: var(--color-text-secondary); margin-top: 4px; }
.info-card { padding: 28px; }
.card-section-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 16px; }
</style>
