'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { PERMS } from '@/lib/permissions'

const NAV = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    perm: null,
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    ),
  },
  {
    href: '/dashboard/agent',
    label: 'AI Agent',
    perm: PERMS.AGENT_CHAT_VIEW,
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path
          d="M12 3C7.03 3 3 6.58 3 11c0 2.12.9 4.06 2.38 5.54L4 21l4.7-1.5A9.7 9.7 0 0012 20c4.97 0 9-3.58 9-8s-4.03-8-9-8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="8.5" cy="11" r="1" fill="currentColor" />
        <circle cx="12" cy="11" r="1" fill="currentColor" />
        <circle cx="15.5" cy="11" r="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    href: '/dashboard/rbac-demo',
    label: 'RBAC Demo',
    perm: null,
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path
          d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.8" />
        <path d="M23 21v-2a4 4 0 00-3-3.87" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <path d="M16 3.13a4 4 0 010 7.75" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/dashboard/documents',
    label: 'Documents',
    perm: PERMS.HR_DOCUMENT_VIEW,
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path
          d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <polyline points="14 2 14 8 20 8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/dashboard/tasks',
    label: 'Task Queue',
    perm: PERMS.TASKS_VIEW,
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
]

const ROLE_COLORS: Record<string, string> = {
  admin: 'var(--accent)',
  hr: 'var(--green)',
  finance: 'var(--rose)',
  viewer: 'var(--muted)',
}

function getRoleBadgeColor(roles: string[]): string {
  for (const [key, color] of Object.entries(ROLE_COLORS)) {
    if (roles.some(r => r.toLowerCase().includes(key))) return color
  }
  return 'var(--muted)'
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, loading } = useAuth()
  const pathname = usePathname()
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (!loading && !user) {
      router.push('/')
    }
  }, [user, loading, router])

  if (loading || !user) {
    return (
      <div style={{ background: 'var(--bg)', color: 'var(--muted)' }} className="h-full flex items-center justify-center">
        <div className="text-sm">Loading...</div>
      </div>
    )
  }

  const roleColor = getRoleBadgeColor(user.roles)
  const primaryRole = user.roles[0] || 'user'

  return (
    <div style={{ background: 'var(--bg)' }} className="h-full flex">
      {/* Sidebar */}
      <aside
        style={{
          background: 'var(--surface)',
          borderRight: '1px solid var(--border)',
          width: 224,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          position: 'sticky',
          top: 0,
        }}
      >
        {/* Logo */}
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div
              style={{
                background: 'var(--accent)',
                borderRadius: 8,
                width: 30,
                height: 30,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span style={{ color: 'var(--text)', fontSize: 16, fontWeight: 700, letterSpacing: '-0.3px' }}>
              OpsCore
            </span>
          </div>
          {user.org && (
            <div style={{ color: 'var(--muted)', fontSize: 11, marginTop: 6, paddingLeft: 2 }}>
              {user.org.name}
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ padding: '12px 10px', flex: 1, overflowY: 'auto' }}>
          {NAV.map(item => {
            const hasAccess = !item.perm || user.permissions.includes(item.perm)
            const isActive = item.href === '/dashboard'
              ? pathname === '/dashboard'
              : pathname.startsWith(item.href)

            return (
              <Link
                key={item.href}
                href={hasAccess ? item.href : '#'}
                onClick={hasAccess ? undefined : e => e.preventDefault()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 10px',
                  borderRadius: 8,
                  marginBottom: 2,
                  color: isActive ? 'var(--accent)' : hasAccess ? 'var(--text)' : 'var(--border)',
                  background: isActive ? 'rgba(79,141,184,0.12)' : 'transparent',
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  textDecoration: 'none',
                  cursor: hasAccess ? 'pointer' : 'not-allowed',
                  transition: 'all 0.15s',
                  opacity: hasAccess ? 1 : 0.4,
                }}
              >
                <span style={{ opacity: hasAccess ? 1 : 0.5 }}>{item.icon}</span>
                {item.label}
                {!hasAccess && (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" style={{ marginLeft: 'auto', opacity: 0.5 }}>
                    <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="2" />
                    <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                )}
              </Link>
            )
          })}
        </nav>

        {/* User info + logout */}
        <div style={{ padding: '12px 14px 16px', borderTop: '1px solid var(--border)' }}>
          <div style={{ marginBottom: 10 }}>
            <div style={{ color: 'var(--text)', fontSize: 12, fontWeight: 600, marginBottom: 2 }}>
              {user.display_name || user.email.split('@')[0]}
            </div>
            <div style={{ color: 'var(--muted)', fontSize: 11, marginBottom: 6 }}>
              {user.email}
            </div>
            <span
              style={{
                background: `${roleColor}22`,
                color: roleColor,
                border: `1px solid ${roleColor}44`,
                borderRadius: 20,
                padding: '2px 8px',
                fontSize: 10,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}
            >
              {primaryRole}
            </span>
          </div>
          <button
            onClick={logout}
            style={{
              width: '100%',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '7px 0',
              color: 'var(--muted)',
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              transition: 'all 0.15s',
            }}
            className="hover:text-[var(--text)] hover:border-[var(--muted)]"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <polyline points="16 17 21 12 16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <line x1="21" y1="12" x2="9" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflowY: 'auto', minHeight: '100vh' }}>
        {children}
      </main>
    </div>
  )
}
