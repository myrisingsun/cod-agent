import { client } from './client'
import type { ExtractionResult } from '../types'

export async function getExtraction(packageId: string): Promise<ExtractionResult> {
  const { data } = await client.get(`/packages/${packageId}/extraction`)
  return data as ExtractionResult
}

export async function retryExtraction(packageId: string): Promise<void> {
  await client.post(`/packages/${packageId}/extraction/retry`)
}
