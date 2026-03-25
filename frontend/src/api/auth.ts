import { client } from './client'
import type { User } from '../types'

export async function login(email: string, password: string): Promise<string> {
  const { data } = await client.post('/auth/login', { email, password })
  return data.access_token as string
}

export async function register(
  email: string,
  password: string,
  full_name: string
): Promise<void> {
  await client.post('/auth/register', { email, password, full_name })
}

export async function getMe(): Promise<User> {
  const { data } = await client.get('/auth/me')
  return data as User
}

export async function logout(): Promise<void> {
  // Backend doesn't have a logout endpoint — just clear client-side token
  // Refresh cookie will expire on its own
}
