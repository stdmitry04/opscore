'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'
import type { Document, TaskRecord } from '@/lib/types'
import { PERMS } from '@/lib/permissions'

interface SearchResult {
  document_name: string
  doc_type: string
  snippet: string
  vector_score: number
  rerank_score?: number
}

const DOC_TYPE_COLOR: Record<string, string> = {
  policy: 'var(--rose)',
  handbook: 'var(--accent)',
  job_description: 'var(--green)',
  other: 'var(--muted)',
}

export default function DocumentsPage() {
  const { user } = useAuth()
  const [documents, setDocuments] = useState<Document[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [uploadContent, setUploadContent] = useState('')
  const [uploadName, setUploadName] = useState('')
  const [uploadType, setUploadType] = useState('policy')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<{ task_id: string } | null>(null)
  const [tasks, setTasks] = useState<Record<string, TaskRecord>>({})
  const fileRef = useRef<HTMLInputElement>(null)

  const canView = user?.permissions.includes(PERMS.HR_DOCUMENT_VIEW)
  const canUpload = user?.permissions.includes(PERMS.HR_DOCUMENT_EDIT)

  const loadDocs = useCallback(async () => {
    if (!canView) return
    try {
      const data = await api.get<{ results: Document[] }>('/hr/documents/')
      setDocuments(data.results || [])
    } catch {}
  }, [canView])

  useEffect(() => { loadDocs() }, [loadDocs])

  // poll task status for documents being indexed
  useEffect(() => {
    const pending = documents.filter(d => !d.is_indexed)
    if (pending.length === 0) return
    const interval = setInterval(async () => {
      try {
        const data = await api.get<{ results: Document[] }>('/hr/documents/')
        const docs = data.results || []
        setDocuments(docs)
        if (docs.every(d => d.is_indexed)) clearInterval(interval)
      } catch {}
    }, 3000)
    return () => clearInterval(interval)
  }, [documents])

  const search = async () => {
    if (!searchQuery.trim() || !canView) return
    setSearching(true)
    setSearchResults(null)
    try {
      const data = await api.get<{ results: SearchResult[]; error?: string }>(
        `/hr/documents/search/?q=${encodeURIComponent(searchQuery)}`
      )
      setSearchResults(data.results)
    } catch {
      setSearchResults([])
    }
    setSearching(false)
  }

  const upload = async () => {
    if (!uploadContent.trim() || !uploadName.trim()) return
    setUploading(true)
    const fd = new FormData()
    fd.append('name', uploadName)
    fd.append('doc_type', uploadType)
    fd.append('content', uploadContent)
    try {
      const res = await api.postFormData<{ document: Document; task_id: string }>('/hr/documents/', fd)
      setUploadResult({ task_id: res.task_id })
      setUploadContent('')
      setUploadName('')
      await loadDocs()
    } catch {}
    setUploading(false)
  }

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setUploadContent(text)
    setUploadName(file.name.replace(/\.[^.]+$/, ''))
  }

  const indexedCount = documents.filter(d => d.is_indexed).length

  if (!canView) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>
        <div style={{ fontSize: '2rem', marginBottom: 12 }}>🔒</div>
        <p>You need <code style={{ color: 'var(--accent)' }}>{PERMS.HR_DOCUMENT_VIEW}</code> to access this page.</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, alignItems: 'start' }}>
      {/* Left: search + results */}
      <div className="space-y-5">
        <div>
          <h1 style={{ color: 'var(--text)', fontSize: '1.4rem', fontWeight: 700 }}>Document Knowledge Base</h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', marginTop: 4 }}>
            {indexedCount} of {documents.length} documents indexed in Qdrant · semantic search with cross-encoder reranking
          </p>
        </div>

        {/* Search */}
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder='e.g. "time off policy" or "interview stages" or "salary bands"'
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 8,
              border: '1px solid var(--border)', background: 'var(--surface-elevated)',
              color: 'var(--text)', fontSize: '0.9rem', outline: 'none',
            }}
          />
          <button
            onClick={search}
            disabled={searching || !searchQuery.trim()}
            style={{
              padding: '10px 20px', borderRadius: 8, border: 'none',
              background: 'var(--accent)', color: 'white', cursor: 'pointer',
              fontSize: '0.9rem', fontWeight: 600, opacity: searching ? 0.6 : 1,
            }}
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Example queries */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {['time off policy', 'salary bands IC4', 'incident severity P1', 'interview process', 'remote work equipment'].map(q => (
            <button
              key={q}
              onClick={() => { setSearchQuery(q); }}
              style={{
                padding: '4px 10px', borderRadius: 20, fontSize: '0.75rem',
                border: '1px solid var(--border)', background: 'transparent',
                color: 'var(--muted)', cursor: 'pointer',
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {/* Search results */}
        {searchResults !== null && (
          <div className="space-y-3">
            <p style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>
              {searchResults.length} results above 70% relevance threshold · sorted by cross-encoder score
            </p>
            {searchResults.length === 0 && (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)', background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border)' }}>
                No results above threshold. Try a different query or upload more documents.
              </div>
            )}
            {searchResults.map((r, i) => (
              <div key={i} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, color: 'var(--text)', fontSize: '0.9rem' }}>{r.document_name}</span>
                    <span style={{ marginLeft: 8, fontSize: '0.7rem', padding: '2px 7px', borderRadius: 10, background: 'var(--surface-elevated)', color: DOC_TYPE_COLOR[r.doc_type] || 'var(--muted)' }}>
                      {r.doc_type}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <span title="Qdrant cosine similarity" style={{ fontSize: '0.72rem', padding: '2px 7px', borderRadius: 6, background: 'rgba(79,141,184,0.1)', color: 'var(--accent)', border: '1px solid rgba(79,141,184,0.2)' }}>
                      vec {r.vector_score}
                    </span>
                    {r.rerank_score !== undefined && (
                      <span title="Cross-encoder rerank score" style={{ fontSize: '0.72rem', padding: '2px 7px', borderRadius: 6, background: 'rgba(110,139,114,0.1)', color: 'var(--green)', border: '1px solid rgba(110,139,114,0.2)' }}>
                        rerank {r.rerank_score}
                      </span>
                    )}
                  </div>
                </div>
                <p style={{ color: 'var(--muted)', fontSize: '0.82rem', lineHeight: 1.6, margin: 0 }}>
                  {r.snippet}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Document list */}
        {!searchResults && (
          <div>
            <p style={{ color: 'var(--muted)', fontSize: '0.8rem', marginBottom: 10 }}>All documents</p>
            <div className="space-y-2">
              {documents.map(doc => (
                <div key={doc.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
                  <div style={{ flex: 1 }}>
                    <span style={{ color: 'var(--text)', fontSize: '0.88rem' }}>{doc.name}</span>
                    <span style={{ marginLeft: 8, fontSize: '0.7rem', color: DOC_TYPE_COLOR[doc.doc_type] || 'var(--muted)' }}>{doc.doc_type}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: doc.is_indexed ? 'var(--green)' : 'var(--rose)' }}>
                    {doc.is_indexed ? (
                      <span>indexed</span>
                    ) : (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1.5s infinite' }} />
                        embedding...
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--muted)' }}>
                    {(doc.file_size / 1024).toFixed(1)}kb
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right: upload */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '20px' }}>
        <h2 style={{ color: 'var(--text)', fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Upload document</h2>

        {!canUpload ? (
          <p style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>You need <code style={{ color: 'var(--accent)' }}>{PERMS.HR_DOCUMENT_EDIT}</code> to upload.</p>
        ) : (
          <div className="space-y-3">
            <input
              value={uploadName}
              onChange={e => setUploadName(e.target.value)}
              placeholder="Document name"
              style={{ width: '100%', padding: '8px 12px', borderRadius: 7, border: '1px solid var(--border)', background: 'var(--surface-elevated)', color: 'var(--text)', fontSize: '0.85rem', boxSizing: 'border-box' }}
            />
            <select
              value={uploadType}
              onChange={e => setUploadType(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 7, border: '1px solid var(--border)', background: 'var(--surface-elevated)', color: 'var(--text)', fontSize: '0.85rem' }}
            >
              <option value="policy">Policy</option>
              <option value="handbook">Handbook</option>
              <option value="job_description">Job Description</option>
              <option value="other">Other</option>
            </select>
            <button
              onClick={() => fileRef.current?.click()}
              style={{ width: '100%', padding: '8px', borderRadius: 7, border: '1px dashed var(--border)', background: 'transparent', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.82rem' }}
            >
              Drop .txt / .md file or click to browse
            </button>
            <input ref={fileRef} type="file" accept=".txt,.md" onChange={handleFile} style={{ display: 'none' }} />
            <textarea
              value={uploadContent}
              onChange={e => setUploadContent(e.target.value)}
              placeholder="Or paste document text here..."
              rows={6}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 7, border: '1px solid var(--border)', background: 'var(--surface-elevated)', color: 'var(--text)', fontSize: '0.82rem', resize: 'vertical', boxSizing: 'border-box' }}
            />
            <button
              onClick={upload}
              disabled={uploading || !uploadContent.trim() || !uploadName.trim()}
              style={{ width: '100%', padding: '9px', borderRadius: 7, border: 'none', background: 'var(--accent)', color: 'white', cursor: 'pointer', fontWeight: 600, fontSize: '0.88rem', opacity: uploading ? 0.7 : 1 }}
            >
              {uploading ? 'Uploading...' : 'Upload & Embed'}
            </button>
            {uploadResult && (
              <p style={{ color: 'var(--green)', fontSize: '0.78rem' }}>
                Queued for embedding · task {uploadResult.task_id.slice(0, 8)}
              </p>
            )}
          </div>
        )}

        <details style={{ marginTop: 20, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
          <summary style={{ color: 'var(--muted)', cursor: 'pointer', fontSize: '0.8rem' }}>How RAG works here</summary>
          <div style={{ color: 'var(--muted)', fontSize: '0.78rem', marginTop: 10, lineHeight: 1.6 }}>
            <p>1. Text chunked into ~120-word windows with 20-word overlap</p>
            <p>2. Each chunk embedded with <code style={{ color: 'var(--accent)' }}>all-MiniLM-L6-v2</code> → stored in Qdrant</p>
            <p>3. On search: embed query → Qdrant cosine similarity → top 20 candidates</p>
            <p>4. <code style={{ color: 'var(--accent)' }}>cross-encoder/ms-marco-MiniLM-L-6-v2</code> rescores each (query, chunk) pair</p>
            <p>5. Filter to rerank score ≥ 0.70, return sorted</p>
          </div>
        </details>
      </div>
    </div>
  )
}
