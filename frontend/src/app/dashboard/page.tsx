'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import type { Analytics } from '@/lib/types'
import { PERMS } from '@/lib/permissions'

function StatCard({
  label,
  value,
  sub,
  locked,
  color,
}: {
  label: string
  value: string | number
  sub?: string
  locked?: boolean
  color?: string
}) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 14,
        padding: '20px 24px',
      }}
    >
      <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 500, marginBottom: 10 }}>
        {label}
      </div>
      {locked ? (
        <div className="flex items-center gap-2">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="11" width="18" height="11" rx="2" stroke="var(--border)" strokeWidth="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" stroke="var(--border)" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <span style={{ color: 'var(--border)', fontSize: 13 }}>No access</span>
        </div>
      ) : (
        <>
          <div
            style={{
              color: color || 'var(--text)',
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: '-0.5px',
              lineHeight: 1,
            }}
          >
            {value}
          </div>
          {sub && (
            <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 6 }}>{sub}</div>
          )}
        </>
      )}
    </div>
  )
}

function DeptBar({ name, count, max }: { name: string; count: number; max: number }) {
  const pct = max > 0 ? (count / max) * 100 : 0
  return (
    <div style={{ marginBottom: 10 }}>
      <div className="flex justify-between mb-1">
        <span style={{ color: 'var(--text)', fontSize: 13 }}>{name}</span>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>{count}</span>
      </div>
      <div
        style={{
          background: 'var(--surface-elevated)',
          borderRadius: 4,
          height: 6,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            background: 'var(--accent)',
            height: '100%',
            width: `${pct}%`,
            borderRadius: 4,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
    </div>
  )
}

function HowItWorks() {
  const [open, setOpen] = useState(false)
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 14,
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          padding: '14px 20px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: 'var(--muted)',
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        How this works
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        >
          <polyline points="6 9 12 15 18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div style={{ padding: '0 20px 16px', color: 'var(--muted)', fontSize: 13, lineHeight: 1.7 }}>
          <p>
            Analytics are computed server-side via Django aggregation queries on the Employee model.
            Results are cached in Redis (TTL: 5 min) keyed by tenant ID, so all users in the same
            org share the same cache entry. Salary data is gated by the{' '}
            <code
              style={{
                background: 'var(--surface-elevated)',
                borderRadius: 4,
                padding: '1px 5px',
                fontFamily: 'monospace',
                fontSize: 11,
              }}
            >
              {PERMS.ANALYTICS_SALARY_REPORT_VIEW}
            </code>{' '}
            permission — the backend checks this before including that field in the response.
          </p>
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const hasSalary = user?.permissions.includes(PERMS.ANALYTICS_SALARY_REPORT_VIEW) ?? false

  useEffect(() => {
    api
      .get<Analytics>('/analytics/')
      .then(setAnalytics)
      .catch(e => setError(e?.data?.detail || 'Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [])

  const roleColor =
    user?.roles?.[0]?.toLowerCase().includes('admin')
      ? 'var(--accent)'
      : user?.roles?.[0]?.toLowerCase().includes('hr')
      ? 'var(--green)'
      : user?.roles?.[0]?.toLowerCase().includes('finance')
      ? 'var(--rose)'
      : 'var(--muted)'

  const maxDept = analytics
    ? Math.max(...analytics.department_breakdown.map(d => d.count), 1)
    : 1

  return (
    <div style={{ padding: '32px 36px', maxWidth: 900 }}>
      {/* Role banner */}
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '12px 18px',
          marginBottom: 28,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <span
          style={{
            background: `${roleColor}22`,
            color: roleColor,
            border: `1px solid ${roleColor}44`,
            borderRadius: 20,
            padding: '3px 10px',
            fontSize: 11,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          {user?.roles?.[0] || 'user'}
        </span>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>
          Signed in as <strong style={{ color: 'var(--text)' }}>{user?.display_name || user?.email}</strong>
        </span>
        <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 12 }}>
          {user?.permissions.length ?? 0} permissions
        </span>
      </div>

      <h1 style={{ color: 'var(--text)', fontSize: 22, fontWeight: 700, marginBottom: 6 }}>
        Workforce Overview
      </h1>
      <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 28 }}>
        Real-time analytics for {user?.org?.name || 'your organization'}
      </p>

      {/* Stat cards */}
      {loading ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 14,
            marginBottom: 28,
          }}
        >
          {[0, 1, 2, 3].map(i => (
            <div
              key={i}
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: 14,
                padding: '20px 24px',
                height: 90,
              }}
            />
          ))}
        </div>
      ) : error ? (
        <div
          style={{
            background: 'rgba(184,118,138,0.1)',
            border: '1px solid rgba(184,118,138,0.2)',
            borderRadius: 12,
            padding: '16px 20px',
            color: 'var(--rose)',
            fontSize: 14,
            marginBottom: 28,
          }}
        >
          {error}
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 14,
            marginBottom: 28,
          }}
        >
          <StatCard
            label="Total Employees"
            value={analytics?.headcount.total ?? '—'}
            sub={`${analytics?.headcount.inactive ?? 0} inactive, ${analytics?.headcount.terminated ?? 0} terminated`}
          />
          <StatCard
            label="Active Employees"
            value={analytics?.headcount.active ?? '—'}
            color="var(--success)"
            sub="Currently employed"
          />
          <StatCard
            label="Open Jobs"
            value={analytics?.open_jobs ?? '—'}
            color="var(--accent)"
            sub="Positions hiring"
          />
          <StatCard
            label="Avg. Salary"
            value={
              hasSalary && analytics?.avg_salary
                ? `$${Math.round(analytics.avg_salary).toLocaleString()}`
                : '—'
            }
            locked={!hasSalary}
            sub="Annual, USD"
          />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        {/* Dept breakdown */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '20px 24px',
          }}
        >
          <h3
            style={{
              color: 'var(--text)',
              fontSize: 14,
              fontWeight: 600,
              marginBottom: 20,
            }}
          >
            Department Breakdown
          </h3>
          {loading ? (
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>Loading...</div>
          ) : analytics?.department_breakdown.length ? (
            analytics.department_breakdown.map(d => (
              <DeptBar key={d.department} name={d.department} count={d.count} max={maxDept} />
            ))
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>No department data</div>
          )}
        </div>

        {/* Permissions panel */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '20px 24px',
          }}
        >
          <h3
            style={{
              color: 'var(--text)',
              fontSize: 14,
              fontWeight: 600,
              marginBottom: 16,
            }}
          >
            Your Permissions
          </h3>
          {user?.permissions.length ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {user.permissions.map(p => (
                <span
                  key={p}
                  style={{
                    background: 'rgba(74,158,107,0.12)',
                    border: '1px solid rgba(74,158,107,0.25)',
                    color: 'var(--success)',
                    borderRadius: 20,
                    padding: '3px 9px',
                    fontSize: 11,
                    fontWeight: 500,
                    fontFamily: 'monospace',
                  }}
                >
                  {p}
                </span>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>No permissions assigned</div>
          )}
        </div>
      </div>

      <HowItWorks />
    </div>
  )
}
