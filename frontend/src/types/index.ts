// User types
export interface User {
  id: string
  email: string
  display_name: string | null
  username: string | null
  role: 'superadmin' | 'admin' | 'user'
  is_active: boolean
  created_at: string
  updated_at: string
}

// API Key types
export interface APIKey {
  id: string
  user_id: string
  provider_id: string | null
  key_prefix: string
  name: string
  status: 'active' | 'suspended' | 'revoked'
  rate_limit_rpm: number
  token_limit_daily: number
  total_tokens_used: number
  allowed_models: string[]
  expires_at: string | null
  created_at: string
  last_used_at: string | null
}

export interface APIKeyCreated extends APIKey {
  full_key: string
}

export interface APIKeyCreate {
  name: string
  rate_limit_rpm?: number
  token_limit_daily?: number
  expires_at?: string | null
  allowed_models?: string[]
}

export interface APIKeyUpdate {
  name?: string
  status?: string
  rate_limit_rpm?: number
  token_limit_daily?: number
  expires_at?: string | null
  allowed_models?: string[]
}

// Auth types
export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

// Stats types
export interface UserStatsSummary {
  total_tokens_used: number
  total_requests: number
  active_keys: number
  total_keys: number
  today_tokens: number
  today_requests: number
}

export interface AdminStatsSummary {
  total_users: number
  total_keys: number
  active_keys: number
  total_tokens_all_time: number
  total_requests_all_time: number
  today_tokens: number
  today_requests: number
}

export interface DailyUsage {
  date: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  request_count: number
}

export interface ModelUsage {
  model: string
  provider_name?: string
  total_tokens: number
  request_count: number
}

export interface KeyUsageSummary {
  key_id: string
  key_prefix: string
  key_name: string
  total_tokens: number
  request_count: number
}

export interface UsageLogItem {
  id: number
  model: string
  provider_name?: string
  endpoint: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  latency_ms: number | null
  status_code: number
  created_at: string
}

// Pagination
export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

// AI Model (managed model list)
export interface AIModel {
  id: string
  provider_id: string | null
  name: string
  display_name: string
  description: string | null
  is_enabled: boolean
  max_tokens: number | null
  context_window: number | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface AIModelCreate {
  provider_id?: string | null
  name: string
  display_name: string
  description?: string | null
  is_enabled?: boolean
  max_tokens?: number | null
  context_window?: number | null
  sort_order?: number
}

export interface AIModelUpdate {
  provider_id?: string | null
  display_name?: string
  description?: string | null
  is_enabled?: boolean
  max_tokens?: number | null
  context_window?: number | null
  sort_order?: number
}

// Provider (API Source)
export interface Provider {
  id: string
  name: string
  display_name: string
  base_url: string
  api_key: string
  description: string | null
  is_enabled: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface ProviderPublic {
  id: string
  name: string
  display_name: string
  description: string | null
  is_enabled: boolean
  sort_order: number
}

export interface ProviderCreate {
  name: string
  display_name: string
  base_url: string
  api_key: string
  description?: string | null
  is_enabled?: boolean
  sort_order?: number
}

export interface ProviderUpdate {
  display_name?: string
  base_url?: string
  api_key?: string
  description?: string | null
  is_enabled?: boolean
  sort_order?: number
}

export interface SyncedModel {
  id: string
  object: string
  created?: number
  owned_by?: string
}

// Application
export interface KeyApplication {
  id: string
  user_id: string
  provider_id: string
  requested_models: string[]
  reason: string
  intended_use: string | null
  status: 'pending' | 'approved' | 'rejected'
  admin_note: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  api_key_id: string | null
  created_at: string
  updated_at: string
  // joined
  provider_name?: string
  provider_display_name?: string
  user_email?: string
  user_display_name?: string
}

export interface KeyApplicationCreate {
  provider_id: string
  requested_models: string[]
  reason: string
  intended_use?: string
}

export interface UserTokenRankingItem {
  user_id: string
  email: string
  display_name: string | null
  total_tokens: number
  request_count: number
}

export interface UserTokenRankingResponse {
  items: UserTokenRankingItem[]
}
