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
let _refreshQueue: Array<(token: string) => void> = []

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      if (_refreshing) {
        // Wait for the in-flight refresh
        return new Promise((resolve) => {
          _refreshQueue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`
            resolve(client(original))
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
        _refreshQueue.forEach((cb) => cb(newToken))
        _refreshQueue = []
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      } catch {
        setAccessToken(null)
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        _refreshing = false
      }
    }
    return Promise.reject(error)
  }
)
