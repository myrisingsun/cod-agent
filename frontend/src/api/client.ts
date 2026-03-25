import axios from 'axios'

const BASE_URL = '/api'

export const client = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // send httpOnly refresh cookie
})

// Access token stored in memory (not localStorage — XSS safe)
let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

// Attach Authorization header
client.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  return config
})

// Auto-refresh on 401
let _refreshing = false
type QueueEntry = { resolve: (token: string) => void; reject: (err: unknown) => void }
let _refreshQueue: QueueEntry[] = []

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      if (_refreshing) {
        // Wait for the in-flight refresh; reject if it fails
        return new Promise((resolve, reject) => {
          _refreshQueue.push({
            resolve: (token) => {
              original.headers.Authorization = `Bearer ${token}`
              resolve(client(original))
            },
            reject,
          })
        })
      }

      _refreshing = true
      try {
        const { data } = await axios.post(
          `${BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        )
        const newToken: string = data.access_token
        setAccessToken(newToken)
        _refreshQueue.forEach(({ resolve }) => resolve(newToken))
        _refreshQueue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch (refreshError) {
        setAccessToken(null)
        // Reject all queued requests so their promises settle (don't hang)
        _refreshQueue.forEach(({ reject }) => reject(refreshError))
        _refreshQueue = []
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        _refreshing = false
      }
    }
    return Promise.reject(error)
  }
)
