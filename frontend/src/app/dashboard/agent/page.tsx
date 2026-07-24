'use client'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import { PERMS } from '@/lib/permissions'

interface ToolCall { tool: string; input: Record<string, unknown>; output: Record<string, unknown> }
interface AgentResult {
  session_id: string
  response: string
  tool_calls: ToolCall[]
  usage: { input_tokens: number; output_tokens: number }
}
interface TaskRecord {
  id: string
  status: 'pending' | 'processing' | 'success' | 'failed' | 'dead_letter'
  result: AgentResult | null
  error: string
}
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  tool_calls?: ToolCall[]
  usage?: { input_tokens: number; output_tokens: number }
  error?: string
}

const TOOL_COLORS: Record<string, string> = {
  search_employees: 'var(--accent)',
  get_employee_detail: '#4DBBBB',
  search_jobs: '#7B8FD4',
  search_documents: '#A47BD4',
  get_analytics: 'var(--green)',
}

const PRESET_QUERIES = [
  { label: 'DB search', queries: [
    'Who are the engineers with the most seniority?',
    'Show me everyone in Finance',
    'Are there any open engineering jobs?',
  ]},
  { label: 'RAG / docs', queries: [
    'What is the remote work equipment stipend?',
    'How does the 401k match work?',
    'What are the P1 incident response steps?',
  ]},
  { label: 'Analytics', queries: [
    'How many employees do we have by department?',
    'Who was hired in the last 90 days?',
    'What are our open roles by department?',
  ]},
]

async function pollAgentTask(taskId: string): Promise<AgentResult> {
  // poll every second for up to 60s — agent chains can take a while
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000))
    const task = await api.get<TaskRecord>(`/tasks/${taskId}/`)
    if (task.status === 'success' && task.result) return task.result
    if (task.status === 'failed' || task.status === 'dead_letter') {
      throw new Error(task.error || 'Agent task failed')
    }
  }
  throw new Error('Agent timed out after 60s')
}

function ToolCallBadge({ call }: { call: ToolCall }) {
  const [open, setOpen] = useState(false)
  const color = TOOL_COLORS[call.tool] || 'var(--muted)'
  return (
    <div style={{ marginBottom: 6 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '4px 10px', borderRadius: 6, border: `1px solid ${color}30`, background: `${color}15`, cursor: 'pointer', color, fontSize: '0.75rem', fontWeight: 600 }}
      >
        <span>⚙</span>
        <span>{call.tool}</span>
        <span style={{ opacity: 0.6 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div style={{ marginTop: 4, marginLeft: 4, padding: '10px 12px', borderRadius: 6, background: 'var(--surface-elevated)', border: '1px solid var(--border)', fontSize: '0.75rem', fontFamily: 'monospace' }}>
          <div style={{ color: 'var(--muted)', marginBottom: 6 }}>input</div>
          <pre style={{ color: 'var(--text)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(call.input, null, 2)}</pre>
          <div style={{ color: 'var(--muted)', marginTop: 10, marginBottom: 6 }}>output</div>
          <pre style={{ color: 'var(--text)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(call.output, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default function AgentPage() {
  const { user } = useAuth()
  const [sessionId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [totalTokens, setTotalTokens] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  const canChat = user?.permissions.includes(PERMS.AGENT_CHAT_VIEW)
  const canSeeTools = user?.permissions.includes(PERMS.AGENT_TOOL_CALLS_VIEW)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text: string) => {
    if (!text.trim() || sending || !canChat) return
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setSending(true)

    try {
      const { task_id } = await api.post<{ task_id: string; session_id: string }>(
        '/agent/chat/',
        { session_id: sessionId, message: text }
      )
      const result = await pollAgentTask(task_id)
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.response,
        tool_calls: result.tool_calls,
        usage: result.usage,
      }
      setMessages(prev => [...prev, assistantMsg])
      if (result.usage) setTotalTokens(t => t + result.usage.input_tokens + result.usage.output_tokens)
    } catch (e: any) {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        error: e?.data?.error || e?.message || 'Request failed. Is ANTHROPIC_API_KEY set?',
      }])
    }
    setSending(false)
  }

  const clearSession = async () => {
    try { await api.del(`/agent/sessions/${sessionId}/`) } catch {}
    setMessages([])
    setTotalTokens(0)
  }

  if (!canChat) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>🔒</div>
        <p>You need <code style={{ color: 'var(--accent)' }}>{PERMS.AGENT_CHAT_VIEW}</code> to use the AI assistant.</p>
        <p style={{ marginTop: 8, fontSize: '0.85rem' }}>Switch to a role with agent access on the RBAC page.</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20, height: 'calc(100vh - 120px)' }}>
      {/* Chat panel */}
      <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ color: 'var(--text)', fontWeight: 600 }}>AI Assistant</span>
            <span style={{ color: 'var(--muted)', fontSize: '0.75rem', marginLeft: 10 }}>claude-sonnet-4-6 · session {sessionId.slice(0, 8)}</span>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {totalTokens > 0 && <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{totalTokens.toLocaleString()} tokens</span>}
            <button onClick={clearSession} style={{ fontSize: '0.75rem', color: 'var(--muted)', background: 'none', border: '1px solid var(--border)', cursor: 'pointer', padding: '4px 8px', borderRadius: 5 }}>Clear</button>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          {messages.length === 0 && (
            <div style={{ color: 'var(--muted)', fontSize: '0.85rem', textAlign: 'center', marginTop: 40 }}>
              <p>Ask anything about employees, jobs, or HR documents.</p>
              <p style={{ marginTop: 6, fontSize: '0.78rem' }}>Use the preset queries on the right to explore different capabilities.</p>
            </div>
          )}
          {messages.map(msg => (
            <div key={msg.id} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                  background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface-elevated)',
                  border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.75rem', color: msg.role === 'user' ? 'white' : 'var(--muted)',
                }}>
                  {msg.role === 'user' ? 'U' : 'AI'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {msg.content && (
                    <p style={{ color: 'var(--text)', fontSize: '0.88rem', lineHeight: 1.65, margin: 0, whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </p>
                  )}
                  {msg.error && (
                    <p style={{ color: 'var(--rose)', fontSize: '0.85rem', margin: 0 }}>{msg.error}</p>
                  )}
                  {canSeeTools && msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      {msg.tool_calls.map((tc, i) => <ToolCallBadge key={i} call={tc} />)}
                    </div>
                  )}
                  {msg.usage && (
                    <p style={{ color: 'var(--muted)', fontSize: '0.7rem', marginTop: 6 }}>
                      {msg.usage.input_tokens} in · {msg.usage.output_tokens} out
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
          {sending && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 }}>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--surface-elevated)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', color: 'var(--muted)' }}>AI</div>
              <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>Thinking...</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) } }}
            placeholder="Ask about employees, jobs, or HR policies..."
            style={{ flex: 1, padding: '9px 13px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface-elevated)', color: 'var(--text)', fontSize: '0.88rem', outline: 'none' }}
          />
          <button
            onClick={() => send(input)}
            disabled={sending || !input.trim()}
            style={{ padding: '9px 16px', borderRadius: 8, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem', opacity: sending ? 0.6 : 1 }}
          >
            Send
          </button>
        </div>
      </div>

      {/* Sidebar: preset queries */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }}>
        {PRESET_QUERIES.map(group => (
          <div key={group.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
            <p style={{ color: 'var(--muted)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10, fontWeight: 600 }}>
              {group.label}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {group.queries.map(q => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  disabled={sending}
                  style={{ textAlign: 'left', padding: '7px 10px', borderRadius: 7, border: '1px solid var(--border)', background: 'var(--surface-elevated)', color: 'var(--text)', cursor: 'pointer', fontSize: '0.8rem', lineHeight: 1.4 }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ))}

        <details style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
          <summary style={{ color: 'var(--muted)', cursor: 'pointer', fontSize: '0.78rem' }}>How memory works</summary>
          <div style={{ color: 'var(--muted)', fontSize: '0.75rem', marginTop: 10, lineHeight: 1.6 }}>
            <p><strong style={{ color: 'var(--text)' }}>Short-term:</strong> conversation history stored in Redis, 20-turn window, 1hr TTL.</p>
            <p style={{ marginTop: 6 }}><strong style={{ color: 'var(--text)' }}>Long-term:</strong> preferences stored in Postgres, injected into the system prompt on every turn.</p>
            <p style={{ marginTop: 6 }}>Try telling the agent "I prefer bullet points" — it'll remember next session.</p>
          </div>
        </details>
      </div>
    </div>
  )
}
