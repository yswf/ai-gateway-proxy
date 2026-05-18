import api from './index'
import type {
  User,
  APIKey,
  APIKeyUpdate,
  AdminStatsSummary,
  DailyUsage,
  ModelUsage,
  KeyUsageSummary,
  PaginatedResponse,
  AIModel,
  AIModelCreate,
  AIModelUpdate,
  Provider,
  ProviderCreate,
  ProviderUpdate,
  SyncedModel,
  KeyApplication,
  UserTokenRankingResponse,
} from '@/types'

export const adminApi = {
  // Users
  listUsers(params?: { skip?: number; limit?: number; search?: string }) {
    return api.get<PaginatedResponse<User>>('/admin/users', { params })
  },
  getUser(id: string) {
    return api.get<User>(`/admin/users/${id}`)
  },
  updateUser(id: string, data: Partial<{ display_name: string; role: string; is_active: boolean; password: string }>) {
    return api.patch<User>(`/admin/users/${id}`, data)
  },

  // Keys
  listAllKeys(params?: { skip?: number; limit?: number; user_id?: string; status?: string }) {
    return api.get<PaginatedResponse<APIKey>>('/admin/keys', { params })
  },
  updateKey(id: string, data: Partial<APIKeyUpdate>) {
    return api.patch<APIKey>(`/admin/keys/${id}`, data)
  },
  deleteKey(id: string) {
    return api.delete(`/admin/keys/${id}`)
  },

  // Analytics
  getSummary() {
    return api.get<AdminStatsSummary>('/admin/analytics/summary')
  },
  getDailyUsage(days = 30) {
    return api.get<DailyUsage[]>('/admin/analytics/daily', { params: { days } })
  },
  getModelUsage(days = 30) {
    return api.get<ModelUsage[]>('/admin/analytics/models', { params: { days } })
  },
  getTopKeys(days = 30, limit = 10) {
    return api.get<KeyUsageSummary[]>('/admin/analytics/top-keys', { params: { days, limit } })
  },
  getUserTokenRanking(limit = 50) {
    return api.get<UserTokenRankingResponse>('/admin/analytics/users/ranking', { params: { limit } })
  },

  // Models
  listModels(params?: { skip?: number; limit?: number }) {
    return api.get<PaginatedResponse<AIModel>>('/admin/models', { params })
  },
  createModel(data: AIModelCreate) {
    return api.post<AIModel>('/admin/models', data)
  },
  updateModel(id: string, data: AIModelUpdate) {
    return api.patch<AIModel>(`/admin/models/${id}`, data)
  },
  deleteModel(id: string) {
    return api.delete(`/admin/models/${id}`)
  },

  // Providers
  listProviders(params?: { skip?: number; limit?: number }) {
    return api.get<PaginatedResponse<Provider>>('/admin/providers', { params })
  },
  createProvider(data: ProviderCreate) {
    return api.post<Provider>('/admin/providers', data)
  },
  updateProvider(id: string, data: ProviderUpdate) {
    return api.patch<Provider>(`/admin/providers/${id}`, data)
  },
  deleteProvider(id: string) {
    return api.delete(`/admin/providers/${id}`)
  },
  syncProviderModels(id: string) {
    return api.get<SyncedModel[]>(`/admin/providers/${id}/sync-models`)
  },

  // Applications (admin)
  listApplications(params?: { skip?: number; limit?: number; status?: string }) {
    return api.get<PaginatedResponse<KeyApplication>>('/admin/applications', { params })
  },
  reviewApplication(id: string, data: { status: 'approved' | 'rejected'; admin_note?: string }) {
    return api.post<KeyApplication>(`/admin/applications/${id}/review`, data)
  },
}
