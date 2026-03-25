import { client } from './client'
import type { ChatMessage, ChatResponse } from '../types'

export async function askQuestion(
  packageId: string,
  question: string
): Promise<ChatResponse> {
  const { data } = await client.post(`/packages/${packageId}/chat`, { question })
  return data as ChatResponse
}

export async function getChatHistory(packageId: string): Promise<ChatMessage[]> {
  const { data } = await client.get(`/packages/${packageId}/chat/history`)
  return data as ChatMessage[]
}
