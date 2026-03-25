export interface User {
  user_id: string
  email: string
  full_name: string
  role: string
}

export type PackageStatus = 'received' | 'processing' | 'parsed' | 'done' | 'error'

export interface Package {
  id: string
  filename: string
  status: PackageStatus
  document_type: string | null
  accuracy: number | null
  user_id: string
  created_at: string
  updated_at: string | null
}

export interface PledgeFields {
  contract_number: string | null
  contract_date: string | null
  pledgee: string | null
  pledgor: string | null
  pledgor_inn: string | null
  pledge_subject: string | null
  cadastral_number: string | null
  area_sqm: number | null
  pledge_value: string | null
  validity_period: string | null
}

export interface FieldConfidence {
  contract_number: number
  contract_date: number
  pledgee: number
  pledgor: number
  pledgor_inn: number
  pledge_subject: number
  cadastral_number: number
  area_sqm: number
  pledge_value: number
  validity_period: number
}

export interface ExtractionResult {
  package_id: string
  fields: PledgeFields
  confidence: FieldConfidence
  accuracy: number | null
  created_at: string
  updated_at: string | null
}

export interface SourceChunk {
  text: string
  score: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceChunk[] | null
  created_at: string
}

export interface ChatResponse {
  answer: string
  sources: SourceChunk[]
  message_id: string
  created_at: string
}
