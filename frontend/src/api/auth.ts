import api from './index'
import type { LoginRequest, TokenResponse, User } from '@/types'

export const authApi = {
  login(data: LoginRequest) {
    return api.post<TokenResponse>('/auth/login', data)
  },

  getOAuthRedirectUrl() {
    return api.get<{ url: string; state: string }>('/auth/oauth/redirect')
  },

  getMe() {
    return api.get<User>('/auth/me')
  },
}
