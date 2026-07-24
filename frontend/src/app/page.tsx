'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

const DEMO_USERS = [
  {
    email: 'admin@acme-demo.com',
    password: 'demo1234',
    role: 'Admin',
    description: 'All permissions',
    color: 'var(--accent)',
  },
  {
    email: 'hr@acme-demo.com',
    password: 'demo1234',
    role: 'HR Manager',
    description: 'Employee & document access',
    color: 'var(--green)',
  },
  {
    email: 'finance@acme-demo.com',
    password: 'demo1234',
    role: 'Finance',
    description: 'Salary & analytics access',
    color: 'var(--rose)',
  },
  {
    email: 'viewer@acme-demo.com',
    password: 'demo1234',
    role: 'Viewer',
    description: 'Read-only access',
    color: 'var(--muted)',
  },
]

export default function LoginPage() {
  const { login, user, loading } = useAuth()
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [quickLoginIdx, setQuickLoginIdx] = useState<number | null>(null)

  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard')
    }
  }, [user, loading, router])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      router.push('/dashboard')
    } catch {
      setError('Invalid credentials. Try one of the demo accounts below.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleQuickLogin(idx: number) {
    const u = DEMO_USERS[idx]
    setQuickLoginIdx(idx)
    setError('')
    try {
      await login(u.email, u.password)
      router.push('/dashboard')
    } catch {
      setError('Could not log in. Is the backend running?')
    } finally {
      setQuickLoginIdx(null)
    }
  }

  if (loading) {
    return (
      <div
        style={{ background: 'var(--bg)', color: 'var(--muted)' }}
        className="h-full flex items-center justify-center"
      >
        <div className="text-sm">Loading...</div>
      </div>
    )
  }

  return (
    <div
      style={{ background: 'var(--bg)' }}
      className="min-h-full flex flex-col items-center justify-center px-4 py-16"
    >
      {/* Header */}
      <div className="mb-10 text-center max-w-lg">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div
            style={{
              background: 'var(--accent)',
              borderRadius: '10px',
              width: 40,
              height: 40,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <h1
            style={{ color: 'var(--text)', fontSize: 28, fontWeight: 700, letterSpacing: '-0.5px' }}
          >
            OpsCore
          </h1>
        </div>
        <p style={{ color: 'var(--accent)', fontSize: 13, fontWeight: 500, marginBottom: 8 }}>
          AI-Powered Workforce Platform
        </p>
        <p style={{ color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>
          A production backend showcase featuring multi-tenant RBAC, AI agents with tool calling +
          RAG, and async task processing with dead-letter queues.
        </p>
      </div>

      <div className="w-full max-w-md">
        {/* Demo credentials card */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: '20px 24px',
            marginBottom: 16,
          }}
        >
          <div
            style={{
              color: 'var(--muted)',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              marginBottom: 14,
            }}
          >
            Demo Accounts
          </div>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_USERS.map((u, idx) => (
              <button
                key={u.email}
                onClick={() => handleQuickLogin(idx)}
                disabled={quickLoginIdx !== null || submitting}
                style={{
                  background:
                    quickLoginIdx === idx ? 'var(--surface-elevated)' : 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 10,
                  padding: '10px 12px',
                  textAlign: 'left',
                  cursor: quickLoginIdx !== null || submitting ? 'not-allowed' : 'pointer',
                  opacity: quickLoginIdx !== null && quickLoginIdx !== idx ? 0.5 : 1,
                  transition: 'all 0.15s',
                }}
                className="hover:opacity-90"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    style={{
                      background: u.color,
                      borderRadius: 4,
                      width: 8,
                      height: 8,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ color: 'var(--text)', fontSize: 12, fontWeight: 600 }}>
                    {u.role}
                  </span>
                  {quickLoginIdx === idx && (
                    <span style={{ color: 'var(--muted)', fontSize: 10 }}>logging in...</span>
                  )}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 11 }}>{u.description}</div>
                <div
                  style={{
                    color: 'var(--muted)',
                    fontSize: 10,
                    marginTop: 4,
                    fontFamily: 'monospace',
                  }}
                >
                  {u.email}
                </div>
              </button>
            ))}
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 11, marginTop: 12 }}>
            All accounts use password:{' '}
            <code
              style={{
                background: 'var(--bg)',
                borderRadius: 4,
                padding: '1px 5px',
                fontFamily: 'monospace',
              }}
            >
              demo1234
            </code>
          </p>
        </div>

        {/* Login form */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: '24px',
          }}
        >
          <h2 style={{ color: 'var(--text)', fontSize: 16, fontWeight: 600, marginBottom: 20 }}>
            Sign in manually
          </h2>

          {error && (
            <div
              style={{
                background: 'rgba(184,118,138,0.12)',
                border: '1px solid rgba(184,118,138,0.3)',
                borderRadius: 8,
                padding: '10px 14px',
                color: 'var(--rose)',
                fontSize: 13,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 500 }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@acme-demo.com"
                required
                style={{
                  display: 'block',
                  width: '100%',
                  background: 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  color: 'var(--text)',
                  fontSize: 14,
                  marginTop: 6,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div>
              <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 500 }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  display: 'block',
                  width: '100%',
                  background: 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  color: 'var(--text)',
                  fontSize: 14,
                  marginTop: 6,
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <button
              type="submit"
              disabled={submitting || quickLoginIdx !== null}
              style={{
                background: 'var(--accent)',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                padding: '11px 0',
                fontSize: 14,
                fontWeight: 600,
                cursor: submitting || quickLoginIdx !== null ? 'not-allowed' : 'pointer',
                opacity: submitting || quickLoginIdx !== null ? 0.7 : 1,
                transition: 'opacity 0.15s',
                width: '100%',
              }}
            >
              {submitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>

        {/* Tech stack pills */}
        <div className="flex flex-wrap gap-2 justify-center mt-8">
          {[
            'Django REST',
            'JWT + RBAC',
            'Claude AI',
            'RAG + pgvector',
            'Celery',
            'Redis',
            'PostgreSQL',
          ].map(tag => (
            <span
              key={tag}
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 20,
                padding: '4px 10px',
                color: 'var(--muted)',
                fontSize: 11,
                fontWeight: 500,
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
