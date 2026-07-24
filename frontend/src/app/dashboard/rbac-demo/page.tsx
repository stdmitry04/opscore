'use client'
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import { PERMS } from '@/lib/permissions'

interface Permission { code: string; description: string }
interface Role { id: string; name: string; description: string; permissions: string[] }

// parse 'hr.employee.view' → { module: 'hr', rest: 'employee.view' }
function parsePermission(code: string) {
  const parts = code.split('.')
  return { module: parts[0], sub: parts.slice(1).join('.'), full: code }
}

function groupByModule(permissions: Permission[]) {
  const groups: Record<string, Permission[]> = {}
  for (const p of permissions) {
    const { module } = parsePermission(p.code)
    if (!groups[module]) groups[module] = []
    groups[module].push(p)
  }
  return groups
}

const MODULE_LABELS: Record<string, string> = {
  hr: 'HR',
  analytics: 'Analytics',
  agent: 'AI Agent',
  tasks: 'Task Queue',
  rbac: 'RBAC Admin',
}

const DEMO_USERS = [
  { email: 'admin@acme-demo.com', password: 'demo1234', label: 'Admin' },
  { email: 'hr@acme-demo.com', password: 'demo1234', label: 'HR Manager' },
  { email: 'finance@acme-demo.com', password: 'demo1234', label: 'Finance' },
  { email: 'viewer@acme-demo.com', password: 'demo1234', label: 'Viewer' },
]

export default function RBACDemoPage() {
  const { user, login } = useAuth()
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [toggling, setToggling] = useState<string | null>(null) // 'roleId:permCode'
  const [lastToggle, setLastToggle] = useState<{ message: string; ok: boolean } | null>(null)
  const [switchingUser, setSwitchingUser] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const isAdmin = user?.permissions.includes(PERMS.RBAC_EDIT)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [permsData, rolesData] = await Promise.all([
        api.get<Permission[]>('/rbac/permissions/'),
        api.get<Role[]>('/rbac/roles/'),
      ])
      setPermissions(permsData)
      setRoles(rolesData)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const hasPermission = (role: Role, code: string) => role.permissions.includes(code)

  const toggle = async (roleId: string, permCode: string, roleName: string) => {
    if (!isAdmin) {
      setLastToggle({ message: `You need ${PERMS.RBAC_EDIT} to modify permissions`, ok: false })
      return
    }
    const key = `${roleId}:${permCode}`
    setToggling(key)
    try {
      const res = await api.post<{ granted: boolean; affected_users: number }>(
        `/rbac/roles/${roleId}/toggle/`,
        { permission_code: permCode }
      )
      setLastToggle({
        message: `${res.granted ? 'Granted' : 'Revoked'} ${permCode} on ${roleName} — ${res.affected_users} user(s) affected, Redis cache cleared`,
        ok: res.granted,
      })
      // re-fetch to reflect actual DB state
      const updated = await api.get<Role[]>('/rbac/roles/')
      setRoles(updated)
    } catch (e: any) {
      setLastToggle({ message: `Error: ${e?.data?.error || 'request failed'}`, ok: false })
    }
    setToggling(null)
  }

  const switchUser = async (email: string, password: string, label: string) => {
    setSwitchingUser(label)
    try {
      await login(email, password)
      await load()
    } catch {}
    setSwitchingUser(null)
  }

  const groups = groupByModule(permissions)
  const moduleOrder = ['hr', 'analytics', 'agent', 'tasks', 'rbac']
  const orderedModules = [
    ...moduleOrder.filter(m => groups[m]),
    ...Object.keys(groups).filter(m => !moduleOrder.includes(m)),
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 style={{ color: 'var(--text)', fontSize: '1.5rem', fontWeight: 700 }}>RBAC Permission Matrix</h1>
        <p style={{ color: 'var(--muted)', marginTop: 4 }}>
          Permissions are defined in <code style={{ color: 'var(--accent)', fontSize: '0.8em' }}>permissions_registry.py</code> and materialized into Postgres on deploy.
          Each cell toggles a grant in the DB and immediately invalidates the Redis permission cache for affected users.
        </p>
      </div>

      {/* Role switcher */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px' }}>
        <p style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Switch demo user — changes what you can toggle
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {DEMO_USERS.map(u => (
            <button
              key={u.email}
              onClick={() => switchUser(u.email, u.password, u.label)}
              disabled={!!switchingUser}
              style={{
                padding: '6px 14px',
                borderRadius: 8,
                border: `1px solid ${user?.email === u.email ? 'var(--accent)' : 'var(--border)'}`,
                background: user?.email === u.email ? 'rgba(79,141,184,0.15)' : 'var(--surface-elevated)',
                color: user?.email === u.email ? 'var(--accent)' : 'var(--muted)',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: user?.email === u.email ? 600 : 400,
              }}
            >
              {switchingUser === u.label ? '...' : u.label}
            </button>
          ))}
        </div>
        {!isAdmin && (
          <p style={{ color: 'var(--rose)', fontSize: '0.8rem', marginTop: 8 }}>
            Current role lacks <code>{PERMS.RBAC_EDIT}</code> — toggles are read-only. Switch to Admin to edit.
          </p>
        )}
      </div>

      {/* Toggle feedback */}
      {lastToggle && (
        <div style={{
          padding: '10px 16px',
          borderRadius: 8,
          border: `1px solid ${lastToggle.ok ? 'var(--green)' : 'var(--rose)'}`,
          background: lastToggle.ok ? 'rgba(110,139,114,0.1)' : 'rgba(184,118,138,0.1)',
          color: lastToggle.ok ? 'var(--green)' : 'var(--rose)',
          fontSize: '0.85rem',
        }}>
          {lastToggle.message}
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--muted)' }}>Loading matrix...</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--muted)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid var(--border)' }}>
                  Permission
                </th>
                {roles.map(role => (
                  <th key={role.id} style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text)', fontSize: '0.85rem', fontWeight: 600, borderBottom: '1px solid var(--border)', minWidth: 90 }}>
                    {role.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orderedModules.map(module => (
                <>
                  <tr key={`group-${module}`}>
                    <td
                      colSpan={roles.length + 1}
                      style={{ padding: '12px 12px 4px', fontSize: '0.7rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.08em' }}
                    >
                      {MODULE_LABELS[module] || module}
                    </td>
                  </tr>
                  {groups[module].map((perm, i) => (
                    <tr
                      key={perm.code}
                      style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}
                    >
                      <td style={{ padding: '8px 12px', fontSize: '0.82rem' }}>
                        <code style={{ color: 'var(--text)', fontSize: '0.8em' }}>{perm.code}</code>
                        <span style={{ display: 'block', color: 'var(--muted)', fontSize: '0.72rem', marginTop: 1 }}>{perm.description}</span>
                      </td>
                      {roles.map(role => {
                        const granted = hasPermission(role, perm.code)
                        const key = `${role.id}:${perm.code}`
                        const isLoading = toggling === key
                        return (
                          <td key={role.id} style={{ textAlign: 'center', padding: '8px 12px' }}>
                            <button
                              onClick={() => toggle(role.id, perm.code, role.name)}
                              disabled={!!toggling || !isAdmin}
                              title={isAdmin ? `Click to ${granted ? 'revoke' : 'grant'}` : 'Need rbac.admin'}
                              style={{
                                width: 28,
                                height: 28,
                                borderRadius: 6,
                                border: `1px solid ${granted ? 'var(--green)' : 'var(--border)'}`,
                                background: granted ? 'rgba(110,139,114,0.2)' : 'transparent',
                                color: granted ? 'var(--green)' : 'var(--border)',
                                cursor: isAdmin ? 'pointer' : 'default',
                                fontSize: '0.9rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto',
                                opacity: isLoading ? 0.4 : 1,
                                transition: 'all 0.15s',
                              }}
                            >
                              {isLoading ? '·' : granted ? '✓' : '○'}
                            </button>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* How it works accordion */}
      <details style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '14px 20px' }}>
        <summary style={{ color: 'var(--muted)', cursor: 'pointer', fontSize: '0.85rem' }}>How this works</summary>
        <div style={{ marginTop: 12, color: 'var(--muted)', fontSize: '0.82rem', lineHeight: 1.6 }}>
          <p>Permissions live in <code style={{ color: 'var(--accent)' }}>permissions_registry.py</code> as a typed list. On every container start, <code style={{ color: 'var(--accent)' }}>sync_permissions()</code> materializes them into Postgres — convergent, safe to run repeatedly. The DB is never the source of truth for what permissions exist.</p>
          <p style={{ marginTop: 8 }}>Toggling a cell calls <code style={{ color: 'var(--accent)' }}>POST /api/rbac/roles/{'{id}'}/toggle/</code>. The server grants or revokes the RolePermission row, then calls <code style={{ color: 'var(--accent)' }}>RBACService.invalidate_cache(user)</code> for every user with that role — deleting their Redis key so the next request gets a fresh grant set.</p>
          <p style={{ marginTop: 8 }}>Cache TTL is 5 minutes. Without invalidation, a revoked permission would still work for up to 5 minutes after the DB change.</p>
        </div>
      </details>
    </div>
  )
}
