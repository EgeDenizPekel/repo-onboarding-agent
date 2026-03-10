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
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-400 w-8 text-right">{pct}%</span>
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
              <div className="mt-1"><ScoreBar score={ev.understanding_score} /></div>
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

function IterationTrace({ iterationLog }) {
  const [expanded, setExpanded] = useState(null)

  if (!iterationLog?.length) return (
    <p className="text-xs text-slate-600 italic">No iteration trace available.</p>
  )

  return (
    <div className="space-y-2">
      {iterationLog.map((iter, i) => (
        <div key={i}>
          <button
            className="w-full text-left bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 rounded-lg p-3 transition-colors"
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-slate-300">Iteration {iter.iteration}</span>
              <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${
                iter.understanding_score >= 0.8 ? 'bg-emerald-900 text-emerald-300' :
                iter.understanding_score >= 0.5 ? 'bg-amber-900 text-amber-300' : 'bg-red-900 text-red-300'
              }`}>{Math.round(iter.understanding_score * 100)}%</span>
            </div>
            <ScoreBar score={iter.understanding_score} />
            {iter.files_explored?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {iter.files_explored.slice(0, 5).map((f, fi) => (
                  <span key={fi} className="px-1.5 py-0.5 text-xs bg-slate-700 text-slate-400 rounded font-mono truncate max-w-[200px]">{f}</span>
                ))}
                {iter.files_explored.length > 5 && (
                  <span className="text-xs text-slate-600">+{iter.files_explored.length - 5} more</span>
                )}
              </div>
            )}
          </button>

          {expanded === i && (
            <div className="mt-1 ml-0 bg-slate-900 border border-slate-700/50 rounded-lg p-4 space-y-4">
              {iter.files_explored?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 mb-2">Files explored ({iter.files_explored.length})</p>
                  <div className="flex flex-col gap-1">
                    {iter.files_explored.map((f, fi) => (
                      <div key={fi} className="flex items-center gap-2">
                        <span className="text-xs text-slate-600 font-mono w-4 shrink-0">{fi + 1}.</span>
                        <span className="text-xs font-mono text-slate-300 bg-slate-800 px-2 py-0.5 rounded">{f}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {iter.reflection_notes && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 mb-1">Reflection</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{iter.reflection_notes}</p>
                </div>
              )}
              {iter.architecture_notes_added?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-400 mb-2">Architecture insights</p>
                  <ul className="space-y-1">
                    {iter.architecture_notes_added.map((note, j) => (
                      <li key={j} className="flex gap-2 text-xs text-slate-300">
                        <span className="text-indigo-400 shrink-0">-</span>{note}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
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

function JobHistoryItem({ job }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [drawerDoc, setDrawerDoc] = useState(null)

  const statusColor = {
    complete: 'text-emerald-400',
    error: 'text-red-400',
    running: 'text-amber-400',
    pending: 'text-slate-400',
  }[job.status] ?? 'text-slate-400'

  async function toggle() {
    if (!expanded && !detail && job.status === 'complete') {
      setLoading(true)
      const res = await fetch(`${API}/jobs/${job.job_id}`)
      const data = await res.json()
      setDetail(data)
      setLoading(false)
    }
    setExpanded(e => !e)
  }

  const iterLog = detail?.result?.iteration_log ?? []
  const doc = detail?.result?.onboarding_document

  return (
    <div className="rounded-lg border border-slate-700/50 overflow-hidden">
      <button
        onClick={toggle}
        className="w-full text-left px-4 py-3 bg-slate-800 hover:bg-slate-700/80 transition-colors"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-slate-200 truncate">{job.repo_url}</span>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`text-xs font-medium ${statusColor}`}>{job.status}</span>
            <span className="text-slate-600 text-xs">{expanded ? '▲' : '▼'}</span>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">{new Date(job.created_at).toLocaleString()}</p>
      </button>

      {expanded && (
        <div className="bg-slate-900 border-t border-slate-700/50 p-4 space-y-4">
          {loading && <p className="text-xs text-slate-500">Loading details...</p>}

          {job.status === 'error' && (
            <p className="text-xs text-red-400">{detail?.error ?? 'Job failed.'}</p>
          )}

          {detail && iterLog.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Exploration Trace - {iterLog.length} iteration{iterLog.length !== 1 ? 's' : ''}
                </p>
                {doc && (
                  <button
                    onClick={() => setDrawerDoc(doc)}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-md transition-colors"
                  >
                    View Document
                  </button>
                )}
              </div>
              <IterationTrace iterationLog={iterLog} />
            </div>
          )}

          {detail && iterLog.length === 0 && doc && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500">No reflection iterations (baseline config).</p>
              <button
                onClick={() => setDrawerDoc(doc)}
                className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-md transition-colors"
              >
                View Document
              </button>
            </div>
          )}
        </div>
      )}

      {drawerDoc && <DocDrawer doc={drawerDoc} onClose={() => setDrawerDoc(null)} />}
    </div>
  )
}

export default function GeneratePage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [focusHint, setFocusHint] = useState('')
  const [status, setStatus] = useState(null)
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
      try { setError(JSON.parse(e.data).message) } catch { setError('Connection error') }
      setStatus('error')
      es.close()
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!repoUrl.trim()) return
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
    setStatus('running')
    startStream(job_id)
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Hero */}
      <h1 className="text-2xl font-bold mb-2">Repo Onboarding Agent</h1>
      <p className="text-slate-300 text-sm mb-1 leading-relaxed">
        Most LLM-based summarizers read a README and call it done. This agent actually explores the codebase - following imports, mapping architecture, and scoring its own understanding in a reflection loop - until it can describe <span className="text-indigo-400 font-medium">how the code works</span>, not just what it does.
      </p>
      <p className="text-slate-500 text-xs mb-8 leading-relaxed">
        Built to explore how reflection loops affect repository onboarding quality. Uses LangGraph for orchestration, a fine-tuned Qwen2.5-7B for exploration decisions, and GPT-4o for synthesis.
      </p>

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
              <JobHistoryItem key={job.job_id} job={job} />
            ))}
          </div>
        </div>
      )}

      {drawerOpen && doc && <DocDrawer doc={doc} onClose={() => setDrawerOpen(false)} />}
    </div>
  )
}
