<template>
  <div class="login-page">
    <!-- Background pattern -->
    <div class="login-bg">
      <div class="bg-blob blob-1"></div>
      <div class="bg-blob blob-2"></div>
    </div>

    <div class="login-wrapper animate-fade-in">
      <!-- Logo -->
      <div class="login-logo">
        <div class="logo-icon">
          <el-icon :size="28"><Connection /></el-icon>
        </div>
        <span class="logo-text gradient-text">AI Gateway</span>
      </div>

      <!-- Card -->
      <div class="login-card">
        <div class="login-card-header">
          <h1 class="login-title">欢迎回来</h1>
          <p class="login-subtitle">登录您的 AI Gateway 控制台</p>
        </div>

        <!-- Tab switcher -->
        <div class="login-tabs">
          <button
            class="tab-btn"
            :class="{ active: tab === 'local' }"
            @click="tab = 'local'"
          >账号密码</button>
          <button
            class="tab-btn"
            :class="{ active: tab === 'oauth' }"
            @click="tab = 'oauth'"
          >Microsoft 登录</button>
        </div>

        <!-- Local Login -->
        <div v-if="tab === 'local'">
          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
                :prefix-icon="User"
                id="input-username"
                autofocus
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                :prefix-icon="Lock"
                id="input-password"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              :loading="loading"
              class="login-btn"
              id="btn-login"
              @click="handleLogin"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form>
        </div>

        <!-- Microsoft OAuth -->
        <div v-else class="oauth-section">
          <p class="oauth-hint">使用您的 Microsoft 企业账号一键登录</p>
          <button class="ms-btn" :disabled="oauthLoading" @click="handleMicrosoft" id="btn-ms-login">
            <span class="ms-icon">
              <svg width="20" height="20" viewBox="0 0 21 21" fill="none">
                <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
              </svg>
            </span>
            <span>{{ oauthLoading ? '跳转中...' : '使用 Microsoft 账号登录' }}</span>
          </button>
        </div>
      </div>

      <p class="login-footer">AI Gateway Proxy &copy; {{ year }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Connection } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const tab = ref<'local' | 'oauth'>('local')
const loading = ref(false)
const oauthLoading = ref(false)
const formRef = ref<FormInstance>()
const year = new Date().getFullYear()

const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login({ username: form.username, password: form.password })
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } finally {
    loading.value = false
  }
}

async function handleMicrosoft() {
  oauthLoading.value = true
  try {
    await auth.loginWithMicrosoft()
  } catch {
    ElMessage.error('无法连接 Microsoft 登录服务')
    oauthLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #f0fdf4 100%);
  position: relative;
  overflow: hidden;
  padding: 24px;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.blob-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2), transparent);
  top: -150px;
  right: -100px;
}

.blob-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.15), transparent);
  bottom: -100px;
  left: -80px;
}

.login-wrapper {
  width: 100%;
  max-width: 440px;
  position: relative;
  z-index: 1;
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 28px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  background: var(--gradient-primary);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
}

.logo-text {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.login-card {
  background: #fff;
  border-radius: var(--radius-xl);
  padding: 36px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04);
}

.login-card-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.login-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-top: 6px;
}

.login-tabs {
  display: flex;
  gap: 4px;
  background: var(--color-bg-subtle);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 4px;
  margin-bottom: 24px;
}

.tab-btn {
  flex: 1;
  padding: 9px 12px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font-sans);
  transition: var(--transition);
  background: transparent;
  color: var(--color-text-secondary);
}

.tab-btn.active {
  background: #fff;
  color: var(--color-primary-dark);
  box-shadow: var(--shadow-sm);
  font-weight: 600;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.oauth-section {
  text-align: center;
}

.oauth-hint {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 20px;
  line-height: 1.6;
}

.ms-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  height: 44px;
  background: #fff;
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition);
}

.ms-btn:hover:not(:disabled) {
  background: var(--color-bg-subtle);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.ms-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ms-icon {
  display: flex;
  align-items: center;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 13px;
  color: var(--color-text-muted);
}

@media (max-width: 480px) {
  .login-card { padding: 24px 20px; }
  .login-logo { margin-bottom: 20px; }
}
</style>
