import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import { getMe } from '../api/auth'
import { setAccessToken } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  signIn: (token: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // On mount: try to restore session via httpOnly refresh cookie
  useEffect(() => {
    let cancelled = false
    axios
      .post('/api/auth/refresh', {}, { withCredentials: true })
      .then(({ data }) => {
        if (cancelled) return
        setAccessToken(data.access_token)
        return getMe()
      })
      .then((user) => {
        if (cancelled || !user) return
        setUser(user)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    // Cleanup: StrictMode fires this twice in dev — cancel the first run
    return () => { cancelled = true }
  }, [])

  async function signIn(token: string) {
    setAccessToken(token)
    const me = await getMe()
    setUser(me)
  }

  function signOut() {
    setAccessToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
