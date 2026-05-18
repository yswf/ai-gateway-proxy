import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.role === 'superadmin')
  const isSuperAdmin = computed(() => user.value?.role === 'superadmin')

  async function login(credentials: LoginRequest) {
    loading.value = true
    try {
      const res = await authApi.login(credentials)
      token.value = res.data.access_token
      localStorage.setItem('access_token', res.data.access_token)
      await fetchMe()
    } finally {
      loading.value = false
    }
  }

  async function loginWithMicrosoft() {
    const res = await authApi.getOAuthRedirectUrl()
    window.location.href = res.data.url
  }

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('access_token', newToken)
  }

  async function fetchMe() {
    try {
      const res = await authApi.getMe()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem('access_token')
  }

  async function init() {
    if (token.value) {
      await fetchMe()
    }
  }

  return {
    user,
    token,
    loading,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    login,
    loginWithMicrosoft,
    setToken,
    fetchMe,
    logout,
    init,
  }
})
