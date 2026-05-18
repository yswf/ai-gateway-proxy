<template>
  <div class="oauth-callback">
    <div class="callback-card glass-card">
      <el-icon class="callback-icon" :class="{ success: !error, error: !!error }">
        <SuccessFilled v-if="!error" />
        <CircleCloseFilled v-else />
      </el-icon>
      <h2>{{ error ? '登录失败' : '登录成功' }}</h2>
      <p>{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SuccessFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const error = ref(false)
const message = ref('正在处理登录...')

onMounted(async () => {
  const token = route.query.token as string
  if (token) {
    auth.setToken(token)
    await auth.fetchMe()
    message.value = '正在跳转...'
    setTimeout(() => router.push('/dashboard'), 1000)
  } else {
    error.value = true
    message.value = '登录失败，请重试'
    setTimeout(() => router.push('/login'), 2000)
  }
})
</script>

<style scoped>
.oauth-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
}
.callback-card {
  padding: 48px;
  text-align: center;
  max-width: 360px;
  width: 100%;
}
.callback-icon {
  font-size: 56px;
  margin-bottom: 20px;
}
.callback-icon.success { color: var(--color-success); }
.callback-icon.error { color: var(--color-danger); }
h2 { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
p { color: var(--color-text-secondary); }
</style>
