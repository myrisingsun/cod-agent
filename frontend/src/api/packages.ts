import { client } from './client'
import type { Package } from '../types'

export async function uploadPackage(file: File): Promise<Package> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post('/packages', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data as Package
}

export async function listPackages(): Promise<Package[]> {
  const { data } = await client.get('/packages')
  return data as Package[]
}

export async function getPackage(id: string): Promise<Package> {
  const { data } = await client.get(`/packages/${id}`)
  return data as Package
}

export async function deletePackage(id: string): Promise<void> {
  await client.delete(`/packages/${id}`)
}
