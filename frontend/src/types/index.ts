export interface User {
  id: string
  email: string
  display_name: string
  role: string
  is_active: boolean
  workspace_id?: string
}

export interface Workspace {
  id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface Node {
  id: string
  title: string
  subtitle?: string
  node_type: string
  body_text?: string
  tags?: string[]
  source_connector?: string
  source_original_id?: string
  chunk_index?: number
  parent_hash?: string
  metadata?: Record<string, unknown>
  workspace_id: string
  created_at: string
  updated_at: string
}

export interface Edge {
  id: string
  source_id: string
  target_id: string
  relationship: string
  weight?: number
  metadata?: Record<string, unknown>
}

export interface IngestJob {
  id: string
  workspace_id: string
  status: "pending" | "running" | "done" | "failed"
  file_name?: string
  file_size?: number
  connector_type?: string
  error_message?: string
  concepts_created?: number
  duplicates_skipped?: number
  total_sections?: number
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  workspace_id?: string
  user_id?: string
  role?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ConnectorConfig {
  id: string
  workspace_id: string
  connector_type: string
  label?: string
  config: Record<string, unknown>
  is_active: boolean
  last_status?: string
  last_error?: string
  created_at: string
  updated_at: string
}

export interface ConnectorTypeInfo {
  type: string
  label: string
  config_schema: Record<string, unknown>
}

export interface AuditLogEntry {
  id: string
  workspace_id?: string
  user_id?: string
  action: string
  resource_type: string
  resource_id?: string
  details?: Record<string, unknown>
  created_at: string
}

export interface ChatResponse {
  answer: string
  citations: Array<{ id: string; title: string; relevance: number }>
  conversation_id: string
}
