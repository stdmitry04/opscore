'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import type { TaskRecord } from '@/lib/types'
import { PERMS } from '@/lib/permissions'

const STATUS_CONFIG: Record<
  TaskRecord['status'],
  { label: string; bg: string; color: string; border: string; pulse?: boolean }
> = {
  pending: {
    label: 'Pending',
    bg: 'rgba(136,153,170,0.1)',
    color: 'var(--muted)',
    border: 'rgba(136,153,170,0.2)',
  },
  processing: {
    label: 'Processing',
    bg: 'rgba(79,141,184,0.12)',
    color: 'var(--accent)',
    border: 'rgba(79,141,184,0.3)',
    pulse: true,
  },
  success: {
    label: 'Success',
    bg: 'rgba(74,158,107,0.12)',
    color: 'var(--success)',
    border: 'rgba(74,158,107,0.25)',
  },
  failed: {
    label: 'Failed',
    bg: 'rgba(184,118,138,0.12)',
    color: 'var(--rose)',
    border: 'rgba(184,118,138,0.25)',
  },
  dead_letter: {
    label: 'Dead Letter',
    bg: 'rgba(251,146,60,0.12)',
    color: '#FB923C',
    border: 'rgba(251,146,60,0.25)',
  },
}

function StatusBadge({ status }: { status: TaskRecord['status'] }) {
  const cfg = STATUS_CONFIG[status]
  return (
    <span
      style={{
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
        borderRadius: 20,
        padding: '3px 10px',
        fontSize: 11,
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
      }}
    >
      {cfg.pulse && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: cfg.color,
            display: 'inline-block',
          }}
          className="animate-pulse-slow"
        />
      )}
      {cfg.label}
    </span>
  )
}

function TaskRow({
  task,
  onRetry,
  canRetry,
}: {
  task: TaskRecord
  onRetry?: (id: string) => void
  canRetry: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        style={{
          borderBottom: '1px solid var(--border)',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(e => !e)}
      >
        <td style={{ padding: '11px 18px' }}>
          <code
            style={{
              fontFamily: 'monospace',
              fontSize: 11,
              color: 'var(--muted)',
            }}
          >
            {task.id.slice(0, 8)}…
          </code>
        </td>
        <td style={{ padding: '11px 18px', color: 'var(--text)', fontSize: 13 }}>
          {task.task_type}
        </td>
        <td style={{ padding: '11px 18px' }}>
          <StatusBadge status={task.status} />
        </td>
        <td style={{ padding: '11px 18px', color: 'var(--muted)', fontSize: 12 }}>
          {task.retry_count}/{task.max_retries}
        </td>
        <td style={{ padding: '11px 18px', color: 'var(--muted)', fontSize: 12 }}>
          {new Date(task.created_at).toLocaleTimeString()}
        </td>
        <td style={{ padding: '11px 18px' }}>
          {(task.status === 'dead_letter' || task.status === 'failed') && canRetry && onRetry && (
            <button
              onClick={e => {
                e.stopPropagation()
                onRetry(task.id)
              }}
              style={{
                background: 'rgba(79,141,184,0.1)',
                border: '1px solid rgba(79,141,184,0.3)',
                borderRadius: 7,
                padding: '4px 10px',
                color: 'var(--accent)',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Retry
            </button>
          )}
        </td>
      </tr>
      {expanded && (
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          <td
            colSpan={6}
            style={{ padding: '0 18px 12px', background: 'var(--bg)' }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, paddingTop: 10 }}>
              <div>
                <div
                  style={{
                    color: 'var(--muted)',
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 4,
                  }}
                >
                  Payload
                </div>
                <pre
                  style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '8px 10px',
                    fontSize: 11,
                    color: 'var(--text)',
                    overflow: 'auto',
                    maxHeight: 120,
                    margin: 0,
                    fontFamily: 'monospace',
                  }}
                >
                  {JSON.stringify(task.payload, null, 2)}
                </pre>
              </div>
              <div>
                <div
                  style={{
                    color: 'var(--muted)',
                    fontSize: 10,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 4,
                  }}
                >
                  Result / Error
                </div>
                <pre
                  style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 6,
                    padding: '8px 10px',
                    fontSize: 11,
                    color: task.error ? 'var(--rose)' : 'var(--text)',
                    overflow: 'auto',
                    maxHeight: 120,
                    margin: 0,
                    fontFamily: 'monospace',
                  }}
                >
                  {task.error
                    ? task.error
                    : task.result
                    ? JSON.stringify(task.result, null, 2)
                    : 'No result yet'}
                </pre>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function HowItWorks() {
  const [open, setOpen] = useState(false)
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: 24,
      }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          padding: '13px 18px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          color: 'var(--muted)',
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        How async task processing works
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        >
          <polyline points="6 9 12 15 18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div style={{ padding: '0 18px 16px', color: 'var(--muted)', fontSize: 13, lineHeight: 1.7 }}>
          Tasks are dispatched via Celery to a Redis broker and processed by worker processes.
          Failed tasks are automatically retried up to{' '}
          <strong style={{ color: 'var(--text)' }}>max_retries</strong> times with exponential
          backoff. After exhausting all retries, tasks are moved to the Dead Letter Queue (DLQ)
          where they can be inspected and manually retried. This page polls the task API every 2
          seconds to show live status — you can click any row to see the full payload and result.
        </div>
      )}
    </div>
  )
}

type FilterTab = 'all' | 'active' | 'dead_letter'

export default function TasksPage() {
  const { user } = useAuth()
  const [tasks, setTasks] = useState<TaskRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<FilterTab>('all')
  const [retrying, setRetrying] = useState<Set<string>>(new Set())
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const canView = user?.permissions.includes(PERMS.TASKS_VIEW) ?? false
  const canRetry = user?.permissions.includes(PERMS.TASKS_EDIT) ?? false

  function loadTasks() {
    if (!canView) return
    api
      .get<{ results: TaskRecord[] }>('/tasks/')
      .then(r => setTasks(r.results || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTasks()
    intervalRef.current = setInterval(loadTasks, 2000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [user])

  async function handleRetry(id: string) {
    setRetrying(prev => new Set([...prev, id]))
    try {
      await api.post(`/tasks/${id}/retry/`)
      loadTasks()
    } catch {
      // silently fail — UI will refresh on next poll
    } finally {
      setRetrying(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  if (!canView) {
    return (
      <div style={{ padding: '32px 36px' }}>
        <h1 style={{ color: 'var(--text)', fontSize: 22, fontWeight: 700, marginBottom: 24 }}>
          Task Queue
        </h1>
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '48px 32px',
            textAlign: 'center',
            maxWidth: 420,
          }}
        >
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" style={{ margin: '0 auto 14px' }}>
            <rect x="3" y="11" width="18" height="11" rx="2" stroke="var(--border)" strokeWidth="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" stroke="var(--border)" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Your role does not have{' '}
            <code
              style={{
                fontFamily: 'monospace',
                fontSize: 12,
                color: 'var(--text)',
                background: 'var(--surface-elevated)',
                borderRadius: 4,
                padding: '1px 5px',
              }}
            >{PERMS.TASKS_VIEW}</code>{' '}
            permission.
          </p>
        </div>
      </div>
    )
  }

  const filtered = tasks.filter(t => {
    if (filter === 'active') return t.status === 'pending' || t.status === 'processing'
    if (filter === 'dead_letter') return t.status === 'dead_letter'
    return true
  })

  const pendingCount = tasks.filter(t => t.status === 'pending').length
  const processingCount = tasks.filter(t => t.status === 'processing').length
  const successCount = tasks.filter(t => t.status === 'success').length
  const dlqCount = tasks.filter(t => t.status === 'dead_letter').length
  const total = tasks.length
  const successRate = total > 0 ? Math.round((successCount / total) * 100) : 0

  const TABS: { key: FilterTab; label: string; count?: number }[] = [
    { key: 'all', label: 'All', count: tasks.length },
    { key: 'active', label: 'Active', count: pendingCount + processingCount },
    { key: 'dead_letter', label: 'Dead Letter', count: dlqCount },
  ]

  return (
    <div style={{ padding: '32px 36px', maxWidth: 960 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <h1 style={{ color: 'var(--text)', fontSize: 22, fontWeight: 700 }}>
          Task Queue
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: 'var(--success)',
            }}
            className="animate-pulse-slow"
          />
          <span style={{ color: 'var(--muted)', fontSize: 12 }}>Live — polling every 2s</span>
        </div>
      </div>
      <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 24 }}>
        Monitor Celery task execution, inspect payloads, and retry failed tasks from the DLQ.
      </p>

      <HowItWorks />

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Pending', value: pendingCount, color: 'var(--muted)' },
          { label: 'Processing', value: processingCount, color: 'var(--accent)', pulse: true },
          { label: 'Success Rate', value: `${successRate}%`, color: 'var(--success)' },
          { label: 'Dead Letter', value: dlqCount, color: '#FB923C' },
        ].map(stat => (
          <div
            key={stat.label}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              padding: '16px 18px',
            }}
          >
            <div style={{ color: 'var(--muted)', fontSize: 11, fontWeight: 500, marginBottom: 8 }}>
              {stat.label}
            </div>
            <div
              style={{
                color: stat.color,
                fontSize: 24,
                fontWeight: 700,
                letterSpacing: '-0.3px',
              }}
            >
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            style={{
              background: filter === tab.key ? 'var(--surface-elevated)' : 'transparent',
              border: `1px solid ${filter === tab.key ? 'var(--border)' : 'transparent'}`,
              borderRadius: 8,
              padding: '6px 14px',
              color: filter === tab.key ? 'var(--text)' : 'var(--muted)',
              fontSize: 13,
              fontWeight: filter === tab.key ? 600 : 400,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              transition: 'all 0.15s',
            }}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span
                style={{
                  background: 'var(--surface)',
                  borderRadius: 10,
                  padding: '1px 7px',
                  fontSize: 11,
                  color: 'var(--muted)',
                }}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Task table */}
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          overflow: 'hidden',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['ID', 'Task Type', 'Status', 'Retries', 'Created', ''].map(h => (
                <th
                  key={h}
                  style={{
                    padding: '10px 18px',
                    textAlign: 'left',
                    color: 'var(--muted)',
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ padding: '24px', color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>
                  Loading...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '32px', color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>
                  {filter === 'dead_letter'
                    ? 'No dead letter tasks — your queue is healthy'
                    : 'No tasks found'}
                </td>
              </tr>
            ) : (
              filtered.map(task => (
                <TaskRow
                  key={task.id}
                  task={task}
                  onRetry={handleRetry}
                  canRetry={canRetry && !retrying.has(task.id)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {filter === 'dead_letter' && dlqCount > 0 && canRetry && (
        <div
          style={{
            marginTop: 16,
            background: 'rgba(251,146,60,0.08)',
            border: '1px solid rgba(251,146,60,0.2)',
            borderRadius: 10,
            padding: '12px 16px',
            color: '#FB923C',
            fontSize: 13,
          }}
        >
          <strong>{dlqCount} task{dlqCount !== 1 ? 's' : ''}</strong> in the dead letter queue.
          Click Retry on individual tasks to re-queue them, or fix the underlying error first.
        </div>
      )}
    </div>
  )
}
