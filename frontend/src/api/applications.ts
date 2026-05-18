import api from './index'
import type { ProviderPublic, AIModel, KeyApplication, KeyApplicationCreate, PaginatedResponse } from '@/types'

export const applicationsApi = {
  // Providers (user-facing, no api_key)
  listProviders() {
    return api.get<PaginatedResponse<ProviderPublic>>('/providers')
  },

  listModelsByProvider(providerId: string) {
    return api.get<PaginatedResponse<AIModel>>(`/providers/${providerId}/models`)
  },

  // Applications
  myApplications(params?: { skip?: number; limit?: number }) {
    return api.get<PaginatedResponse<KeyApplication>>('/applications', { params })
  },

  submit(data: KeyApplicationCreate) {
    return api.post<KeyApplication>('/applications', data)
  },

  withdraw(id: string) {
    return api.delete(`/applications/${id}`)
  },
}
