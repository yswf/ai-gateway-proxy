import api from './index'
import type {
  UserStatsSummary,
  DailyUsage,
  ModelUsage,
  PaginatedResponse,
  UsageLogItem,
} from '@/types'

export const statsApi = {
  getSummary() {
    return api.get<UserStatsSummary>('/stats/summary')
  },

  getDailyUsage(days = 30) {
    return api.get<DailyUsage[]>('/stats/daily', { params: { days } })
  },

  getModelUsage(days = 30) {
    return api.get<ModelUsage[]>('/stats/models', { params: { days } })
  },

  getLogs(params?: { skip?: number; limit?: number; key_id?: string }) {
    return api.get<PaginatedResponse<UsageLogItem>>('/stats/logs', { params })
  },
}
