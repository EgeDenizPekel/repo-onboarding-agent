import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

const API = '/api'
const CONFIGS = ['baseline', 'no_reflection', 'full']
const CONFIG_LABELS = { baseline: 'Baseline', no_reflection: 'No Reflection', full: 'Full' }
const CONFIG_COLORS = {
  baseline: 'border-slate-600 text-slate-300',
  no_reflection: 'border-amber-600 text-amber-300',
  full: 'border-indigo-600 text-indigo-300',
}
const CONFIG_HEADER_BG = {
  baseline: 'bg-slate-800/60',
  no_reflection: 'bg-amber-950/40',
  full: 'bg-indigo-950/40',
}

function ScoreBadge({ score }) {
  const pct = Math.round((score ?? 0) * 100)
  const color = pct >= 80 ? 'bg-emerald-900 text-emerald-300' : pct >= 50 ? 'bg-amber-900 text-amber-300' : 'bg-red-900 text-red-300'
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-semibold ${color}`}>{pct}%</span>
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

function MetricRow({ label, value, format = 'pct' }) {
  const display = value == null ? '-' : format === 'pct' ? `${(value * 100).toFixed(0)}%` : value
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-800/50 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-semibold text-slate-200 tabular-nums">{display}</span>
    </div>
  )
}

function IterationStepper({ iterations }) {
  const [expanded, setExpanded] = useState(null)

  if (!iterations?.length) {
    return <p className="text-xs text-slate-600 italic">No iteration data available for this config.</p>
  }

  return (
    <div className="relative">
      {/* vertical line */}
      <div className="absolute left-3 top-4 bottom-4 w-px bg-slate-700" />

      <div className="space-y-3">
        {iterations.map((iter, i) => (
          <div key={i} className="relative pl-8">
            {/* dot */}
            <div className="absolute left-0 top-3 w-6 h-6 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center">
              <span className="text-xs font-mono text-slate-400">{iter.iteration}</span>
            </div>

            <button
              className="w-full text-left bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-lg p-3 transition-colors"
              onClick={() => setExpanded(expanded === i ? null : i)}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-xs font-medium text-slate-300">Iteration {iter.iteration}</span>
                <ScoreBadge score={iter.understanding_score} />
              </div>
              <ScoreBar score={iter.understanding_score} />

              {iter.files_explored?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {iter.files_explored.slice(0, 4).map(f => (
                    <span key={f} className="px-1.5 py-0.5 text-xs bg-slate-700 text-slate-400 rounded font-mono truncate max-w-[160px]">{f}</span>
                  ))}
                  {iter.files_explored.length > 4 && (
                    <span className="text-xs text-slate-600">+{iter.files_explored.length - 4} more</span>
                  )}
                </div>
              )}
            </button>

            {expanded === i && (
              <div className="mt-2 ml-0 bg-slate-900 border border-slate-700/50 rounded-lg p-4 space-y-4">
                {iter.files_explored?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-2">Files explored</p>
                    <div className="flex flex-wrap gap-1">
                      {iter.files_explored.map(f => (
                        <span key={f} className="px-1.5 py-0.5 text-xs bg-slate-800 text-slate-300 rounded font-mono">{f}</span>
                      ))}
                    </div>
                  </div>
                )}

                {iter.reflection_notes && (
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-2">Reflection</p>
                    <p className="text-xs text-slate-300 leading-relaxed">{iter.reflection_notes}</p>
                  </div>
                )}

                {iter.architecture_notes_added?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-slate-400 mb-2">Architecture insights</p>
                    <ul className="space-y-1">
                      {iter.architecture_notes_added.map((note, j) => (
                        <li key={j} className="flex gap-2 text-xs text-slate-300">
                          <span className="text-indigo-400 shrink-0">-</span>
                          <span>{note}</span>
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
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none">&times;</button>
        </div>
        <article className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{doc}</ReactMarkdown>
        </article>
      </div>
    </div>
  )
}

function ConfigColumn({ config, data }) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const hasDoc = !!data?.onboarding_document
  const hasTrace = data?.iteration_log?.length > 0

  return (
    <div className={`flex flex-col border rounded-xl overflow-hidden border-slate-700 ${CONFIG_HEADER_BG[config]}`}>
      {/* Header */}
      <div className={`px-4 py-3 border-b border-slate-700 ${CONFIG_HEADER_BG[config]}`}>
        <h3 className={`text-sm font-semibold ${CONFIG_COLORS[config].split(' ')[1]}`}>{CONFIG_LABELS[config]}</h3>
      </div>

      <div className="flex-1 p-4 space-y-6">
        {!data || data.status === 'error' ? (
          <p className="text-xs text-red-400">{data?.error ?? 'No data'}</p>
        ) : (
          <>
            {/* Metrics */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Metrics</p>
              <MetricRow label="Architecture Coverage" value={data.architecture_coverage} />
              <MetricRow label="File Ref Accuracy" value={data.file_ref_accuracy} />
              <MetricRow label="Entry Point Accuracy" value={data.entry_point_accuracy} />
              <MetricRow label="Judge Score" value={data.judge_score} format="raw" />
              <MetricRow label="Iterations Used" value={data.iterations_used} format="raw" />
            </div>

            {/* Judge reasoning */}
            {data.judge_reasoning && (
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Judge Reasoning</p>
                <p className="text-xs text-slate-400 leading-relaxed">{data.judge_reasoning}</p>
              </div>
            )}

            {/* View doc button */}
            {hasDoc && (
              <button
                onClick={() => setDrawerOpen(true)}
                className="w-full py-2 bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-600/40 text-indigo-300 text-xs font-medium rounded-lg transition-colors"
              >
                View Onboarding Document
              </button>
            )}

            {/* Iteration stepper */}
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                {hasTrace ? 'Iteration Trace' : 'No Reflection Trace'}
              </p>
              <IterationStepper iterations={data.iteration_log} />
            </div>
          </>
        )}
      </div>

      {drawerOpen && data?.onboarding_document && (
        <DocDrawer doc={data.onboarding_document} onClose={() => setDrawerOpen(false)} />
      )}
    </div>
  )
}

function mergeResults(runs, repoSlug) {
  const merged = {}
  for (const [runId, run] of Object.entries(runs)) {
    if (!runId.includes('gpt4o_mini')) continue
    const repoData = run.repos[repoSlug]
    if (repoData) Object.assign(merged, repoData)
  }
  return merged
}

export default function RepoDetailPage() {
  const { owner, repo } = useParams()
  const repoSlug = `${owner}/${repo}`

  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API}/eval/results`)
      .then(r => r.json())
      .then(data => {
        const merged = mergeResults(data.runs, repoSlug)
        setResults(merged)
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [repoSlug])

  if (loading) return <div className="p-10 text-slate-400">Loading...</div>
  if (error) return <div className="p-10 text-red-400">Error: {error}</div>
  if (!results || Object.keys(results).length === 0) {
    return <div className="p-10 text-slate-400">No results found for {repoSlug}</div>
  }

  return (
    <div className="px-6 py-10">
      <div className="mb-6">
        <Link to="/benchmark" className="text-xs text-indigo-400 hover:text-indigo-300">&larr; Benchmark</Link>
        <h1 className="text-2xl font-bold mt-2 font-mono">{repoSlug}</h1>
        <a
          href={`https://github.com/${repoSlug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-slate-500 hover:text-slate-400"
        >
          github.com/{repoSlug}
        </a>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {CONFIGS.map(cfg => (
          <ConfigColumn key={cfg} config={cfg} data={results[cfg]} />
        ))}
      </div>
    </div>
  )
}
