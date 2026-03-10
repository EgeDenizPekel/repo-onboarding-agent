import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

const API = '/api'

const NODE_LABELS = {
  clone_repo: 'Cloning repository',
  initialize_exploration: 'Reading README & dependencies',
  plan_next_exploration: 'Planning next files to explore',
  explore_files: 'Exploring files',
  reflect: 'Reflecting on understanding',
  synthesize: 'Synthesizing onboarding guide',
  validate: 'Validating file references',
  refine: 'Refining document',
}

function ScoreBar({ score }) {
  const pct = Math.round((score ?? 0) * 100)
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-sm font-mono text-slate-300 w-10 text-right">{pct}%</span>
    </div>
  )
}

function NodeTimeline({ events }) {
  return (
    <div className="space-y-2">
      {events.map((ev, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="mt-1 w-2 h-2 rounded-full bg-indigo-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-300">{NODE_LABELS[ev.node] ?? ev.node}</p>
            {ev.understanding_score != null && (
              <div className="mt-1">
                <ScoreBar score={ev.understanding_score} />
              </div>
            )}
            {ev.files_explored?.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {ev.files_explored.map(f => (
                  <span key={f} className="px-1.5 py-0.5 text-xs bg-slate-700 text-slate-400 rounded font-mono truncate max-w-xs">{f}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function DocDrawer({ doc, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/50" onClick={onClose} />
      <div className="w-full max-w-3xl bg-slate-900 border-l border-slate-700 overflow-y-auto p-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold">Onboarding Document</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">&times;</button>
        </div>
        <article className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{doc}</ReactMarkdown>
        </article>
      </div>
    </div>
  )
}

function JobHistoryItem({ job, onSelect }) {
  const statusColor = {
    complete: 'text-emerald-400',
    error: 'text-red-400',
    running: 'text-amber-400',
    pending: 'text-slate-400',
  }[job.status] ?? 'text-slate-400'

  return (
    <button
      onClick={() => onSelect(job.job_id)}
      className="w-full text-left px-4 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-slate-200 truncate">{job.repo_url}</span>
        <span className={`text-xs font-medium shrink-0 ${statusColor}`}>{job.status}</span>
      </div>
      <p className="text-xs text-slate-500 mt-0.5">{new Date(job.created_at).toLocaleString()}</p>
    </button>
  )
}

export default function GeneratePage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [focusHint, setFocusHint] = useState('')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null) // pending | running | complete | error
  const [events, setEvents] = useState([])
  const [doc, setDoc] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [history, setHistory] = useState([])
  const [error, setError] = useState(null)
  const esRef = useRef(null)

  useEffect(() => {
    fetch(`${API}/jobs`)
      .then(r => r.json())
      .then(d => setHistory(d.jobs ?? []))
      .catch(() => {})
  }, [])

  function startStream(id) {
    if (esRef.current) esRef.current.close()
    const es = new EventSource(`${API}/stream/${id}`)
    esRef.current = es

    es.addEventListener('node_start', (e) => {
      const data = JSON.parse(e.data)
      setEvents(prev => [...prev, { type: 'node_start', node: data.node }])
    })
    es.addEventListener('node_complete', (e) => {
      const data = JSON.parse(e.data)
      setEvents(prev => [...prev, {
        type: 'node_complete',
        node: data.node,
        understanding_score: data.understanding_score,
        files_explored: data.files_explored,
        reflection_notes: data.reflection_notes,
      }])
    })
    es.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data)
      setDoc(data.onboarding_document)
      setStatus('complete')
      es.close()
      fetch(`${API}/jobs`).then(r => r.json()).then(d => setHistory(d.jobs ?? []))
    })
    es.addEventListener('error', (e) => {
      try {
        const data = JSON.parse(e.data)
        setError(data.message)
      } catch {
        setError('Connection error')
      }
      setStatus('error')
      es.close()
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!repoUrl.trim()) return
    setJobId(null)
    setStatus('pending')
    setEvents([])
    setDoc(null)
    setError(null)

    const res = await fetch(`${API}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl.trim(), focus_hint: focusHint.trim() }),
    })
    const { job_id } = await res.json()
    setJobId(job_id)
    setStatus('running')
    startStream(job_id)
  }

  async function loadJob(id) {
    const res = await fetch(`${API}/jobs/${id}`)
    const job = await res.json()
    setJobId(id)
    setStatus(job.status)
    setEvents([])
    setError(job.error ?? null)
    if (job.status === 'complete' && job.result) {
      setDoc(job.result.onboarding_document ?? null)
    } else if (job.status === 'running' || job.status === 'pending') {
      startStream(id)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold mb-1">Generate Onboarding Guide</h1>
      <p className="text-slate-400 text-sm mb-8">Paste a GitHub repo URL and the agent will explore it and produce a developer onboarding document.</p>

      <form onSubmit={handleSubmit} className="space-y-4 mb-10">
        <div>
          <label className="block text-sm text-slate-400 mb-1">GitHub URL</label>
          <input
            type="url"
            value={repoUrl}
            onChange={e => setRepoUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            required
            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Focus hint <span className="text-slate-600">(optional)</span></label>
          <input
            type="text"
            value={focusHint}
            onChange={e => setFocusHint(e.target.value)}
            placeholder="e.g. focus on the authentication flow"
            className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={status === 'running' || status === 'pending'}
          className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
        >
          {status === 'running' || status === 'pending' ? 'Running...' : 'Generate'}
        </button>
      </form>

      {/* Progress */}
      {status && status !== 'complete' && status !== 'error' && events.length > 0 && (
        <div className="mb-8 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Agent Progress</h2>
          <NodeTimeline events={events.filter(e => e.type === 'node_complete')} />
        </div>
      )}

      {/* Error */}
      {status === 'error' && (
        <div className="mb-8 bg-red-950 border border-red-800 rounded-xl p-5 text-red-300 text-sm">
          {error ?? 'An error occurred.'}
        </div>
      )}

      {/* Complete */}
      {status === 'complete' && doc && (
        <div className="mb-8 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-emerald-400">Done</p>
              <p className="text-xs text-slate-500 mt-0.5">Onboarding document generated</p>
            </div>
            <button
              onClick={() => setDrawerOpen(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              View Document
            </button>
          </div>
          <div className="mt-4 border-t border-slate-800 pt-4">
            <NodeTimeline events={events.filter(e => e.type === 'node_complete')} />
          </div>
        </div>
      )}

      {/* Job history */}
      {history.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Previous Jobs</h2>
          <div className="space-y-2">
            {history.map(job => (
              <JobHistoryItem key={job.job_id} job={job} onSelect={loadJob} />
            ))}
          </div>
        </div>
      )}

      {drawerOpen && doc && <DocDrawer doc={doc} onClose={() => setDrawerOpen(false)} />}
    </div>
  )
}
