import api from './index'
import type { APIKey, APIKeyCreated, APIKeyCreate, APIKeyUpdate, PaginatedResponse } from '@/types'

export const apiKeysApi = {
  list(params?: { skip?: number; limit?: number }) {
    return api.get<PaginatedResponse<APIKey>>('/keys', { params })
  },

  create(data: APIKeyCreate) {
    return api.post<APIKeyCreated>('/keys', data)
  },

  get(id: string) {
    return api.get<APIKey>(`/keys/${id}`)
  },

  update(id: string, data: Partial<APIKeyUpdate>) {
    return api.patch<APIKey>(`/keys/${id}`, data)
  },

  revoke(id: string) {
    return api.delete(`/keys/${id}`)
  },
}
