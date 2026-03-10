import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const API = '/api'
const CONFIGS = ['baseline', 'no_reflection', 'full']
const CONFIG_LABELS = { baseline: 'Baseline', no_reflection: 'No Reflection', full: 'Full' }
const CONFIG_COLORS = { baseline: 'text-slate-400', no_reflection: 'text-amber-400', full: 'text-indigo-400' }

function MetricCell({ value, format = 'pct' }) {
  if (value == null) return <td className="px-4 py-2 text-slate-600 text-center">-</td>
  const display = format === 'pct' ? `${(value * 100).toFixed(0)}%` : value
  return <td className="px-4 py-2 text-center text-slate-200 tabular-nums">{display}</td>
}

function AblationBar({ label, values, color }) {
  const max = 1
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-28 shrink-0 text-right">{label}</span>
      <div className="flex-1 flex flex-col gap-1">
        {CONFIGS.map(cfg => {
          const v = values[cfg] ?? 0
          const pct = Math.round(v * 100)
          return (
            <div key={cfg} className="flex items-center gap-2">
              <span className={`text-xs w-24 shrink-0 ${CONFIG_COLORS[cfg]}`}>{CONFIG_LABELS[cfg]}</span>
              <div className="flex-1 h-4 bg-slate-800 rounded overflow-hidden">
                <div
                  className={`h-full rounded transition-all duration-700 ${
                    cfg === 'full' ? 'bg-indigo-500' : cfg === 'no_reflection' ? 'bg-amber-500' : 'bg-slate-600'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs text-slate-400 tabular-nums w-8">{pct}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function mergeResults(runs) {
  // Merge all gpt4o_mini runs, later runs overwrite earlier for same repo
  const merged = {}
  for (const [runId, run] of Object.entries(runs)) {
    if (!runId.includes('gpt4o_mini')) continue
    for (const [repo, results] of Object.entries(run.repos)) {
      merged[repo] = { ...(merged[repo] ?? {}), ...results }
    }
  }
  return merged
}

function aggregate(repos, metric) {
  const result = {}
  for (const cfg of CONFIGS) {
    const vals = Object.values(repos)
      .map(r => r[cfg])
      .filter(r => r?.status === 'ok')
      .map(r => r[metric])
      .filter(v => v != null)
    result[cfg] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
  }
  return result
}

export default function BenchmarkPage() {
  const [repos, setRepos] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${API}/eval/results`)
      .then(r => r.json())
      .then(data => {
        setRepos(mergeResults(data.runs))
        setLoading(false)
      })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div className="p-10 text-slate-400">Loading benchmark results...</div>
  if (error) return <div className="p-10 text-red-400">Error: {error}</div>

  const archCov = aggregate(repos, 'architecture_coverage')
  const fileRef = aggregate(repos, 'file_ref_accuracy')
  const judge = aggregate(repos, 'judge_score')

  const repoList = Object.entries(repos).sort(([a], [b]) => a.localeCompare(b))

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold mb-1">Benchmark Results</h1>
      <p className="text-slate-400 text-sm mb-10">
        Ablation study across 20 repositories comparing three agent configurations.
      </p>

      {/* Ablation charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {[
          { label: 'Architecture Coverage', metric: archCov },
          { label: 'File Ref Accuracy', metric: fileRef },
          { label: 'Judge Score (normalized)', metric: { baseline: (judge.baseline ?? 0) / 5, no_reflection: (judge.no_reflection ?? 0) / 5, full: (judge.full ?? 0) / 5 } },
        ].map(({ label, metric }) => (
          <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">{label}</h3>
            <div className="space-y-3">
              {CONFIGS.map(cfg => {
                const v = metric[cfg] ?? 0
                const pct = Math.round(v * 100)
                return (
                  <div key={cfg} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className={CONFIG_COLORS[cfg]}>{CONFIG_LABELS[cfg]}</span>
                      <span className="text-slate-400 tabular-nums">{pct}%</span>
                    </div>
                    <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          cfg === 'full' ? 'bg-indigo-500' : cfg === 'no_reflection' ? 'bg-amber-500' : 'bg-slate-600'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Per-repo table */}
      <h2 className="text-lg font-semibold mb-4">Per-Repository Results</h2>
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900">
              <th className="px-4 py-3 text-left text-slate-400 font-medium">Repository</th>
              {CONFIGS.map(cfg => (
                <th key={cfg} colSpan={3} className={`px-4 py-3 text-center font-medium ${CONFIG_COLORS[cfg]}`}>
                  {CONFIG_LABELS[cfg]}
                </th>
              ))}
            </tr>
            <tr className="border-b border-slate-800 bg-slate-900/50">
              <th className="px-4 py-2" />
              {CONFIGS.map(cfg => (
                <>
                  <th key={`${cfg}-arch`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">ArchCov</th>
                  <th key={`${cfg}-ref`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">FileRef</th>
                  <th key={`${cfg}-judge`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">Judge</th>
                </>
              ))}
            </tr>
          </thead>
          <tbody>
            {repoList.map(([repoSlug, results], i) => {
              const [owner, repo] = repoSlug.split('/')
              return (
                <tr key={repoSlug} className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${i % 2 === 0 ? '' : 'bg-slate-900/30'}`}>
                  <td className="px-4 py-2">
                    <Link
                      to={`/benchmark/${owner}/${repo}`}
                      className="text-indigo-400 hover:text-indigo-300 font-mono text-xs"
                    >
                      {repoSlug}
                    </Link>
                  </td>
                  {CONFIGS.map(cfg => {
                    const r = results[cfg]
                    if (!r || r.status === 'error') {
                      return (
                        <>
                          <td key={`${cfg}-arch`} className="px-4 py-2 text-center text-red-500 text-xs" colSpan={3}>error</td>
                        </>
                      )
                    }
                    return (
                      <>
                        <MetricCell key={`${cfg}-arch`} value={r.architecture_coverage} />
                        <MetricCell key={`${cfg}-ref`} value={r.file_ref_accuracy} />
                        <td key={`${cfg}-judge`} className="px-4 py-2 text-center text-slate-200 tabular-nums">{r.judge_score}/5</td>
                      </>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
