'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { AuthUser } from '@/lib/auth'
import { setTokens, clearTokens } from '@/lib/api'
import { useRouter } from 'next/navigation'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  switchUser: (email: string, password: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

// Only the refresh token (not access token) is persisted to sessionStorage.
// sessionStorage is scoped to the tab and cleared when the tab is closed.
// Access tokens live only in module-level memory — never written to any storage.
const SESSION_REFRESH_KEY = 'opscore_rt'
const SESSION_USER_KEY = 'opscore_user'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Restore session: re-hydrate user data and refresh token from sessionStorage
    const savedRefresh = sessionStorage.getItem(SESSION_REFRESH_KEY)
    const savedUser = sessionStorage.getItem(SESSION_USER_KEY)
    if (savedRefresh && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser) as AuthUser
        // Restore refresh token into the api module; access token will be fetched on next 401
        setTokens('', savedRefresh)
        setUser(parsedUser)
      } catch {
        sessionStorage.removeItem(SESSION_REFRESH_KEY)
        sessionStorage.removeItem(SESSION_USER_KEY)
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const { api } = await import('@/lib/api')
      // Call the token endpoint directly so we can intercept the refresh token
      const tokens = await api.post<{ access: string; refresh: string }>('/auth/token/', {
        email,
        password,
      })
      setTokens(tokens.access, tokens.refresh)

      const loggedInUser = await api.get<AuthUser>('/auth/me/')
      setUser(loggedInUser)

      // Persist only refresh token + user data — access token stays in memory
      sessionStorage.setItem(SESSION_REFRESH_KEY, tokens.refresh)
      sessionStorage.setItem(SESSION_USER_KEY, JSON.stringify(loggedInUser))
    },
    []
  )

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    sessionStorage.removeItem(SESSION_REFRESH_KEY)
    sessionStorage.removeItem(SESSION_USER_KEY)
    router.push('/')
  }, [router])

  const switchUser = useCallback(async (email: string, password: string) => {
    clearTokens()
    const { api } = await import('@/lib/api')
    const tokens = await api.post<{ access: string; refresh: string }>('/auth/token/', {
      email,
      password,
    })
    setTokens(tokens.access, tokens.refresh)
    const loggedInUser = await api.get<AuthUser>('/auth/me/')
    setUser(loggedInUser)
    sessionStorage.setItem(SESSION_REFRESH_KEY, tokens.refresh)
    sessionStorage.setItem(SESSION_USER_KEY, JSON.stringify(loggedInUser))
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, switchUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function useRequireAuth() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/')
    }
  }, [user, loading, router])

  return { user, loading }
}
