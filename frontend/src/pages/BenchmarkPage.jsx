import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import AgentGraph from '../components/AgentGraph'

const API = '/api'
const CONFIGS = ['baseline', 'no_reflection', 'full']
const CONFIG_LABELS = { baseline: 'Baseline', no_reflection: 'No Reflection', full: 'Full' }
const CONFIG_COLORS = { baseline: 'text-slate-400', no_reflection: 'text-amber-400', full: 'text-indigo-400' }

const METRIC_DESCRIPTIONS = {
  ArchCov: 'Architecture Coverage - fraction of high-import modules mentioned in the onboarding document. Measures how well the agent captures the core architectural components.',
  FileRef: 'File Reference Accuracy - fraction of file paths cited in the document that actually exist in the repository. Measures hallucination rate for file references.',
  Judge: 'Judge Score (1-5) - GPT-4o coherence rating of the onboarding document. Evaluates clarity, completeness, and usefulness for a new developer.',
}

function Tooltip({ text, children }) {
  const [pos, setPos] = useState(null)
  const ref = useRef(null)

  function show() {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    setPos({
      top: rect.top - 8,
      left: rect.left + rect.width / 2,
    })
  }

  function hide() { setPos(null) }

  return (
    <>
      <span ref={ref} onMouseEnter={show} onMouseLeave={hide} className="inline-block">
        {children}
      </span>
      {pos && (
        <span
          className="fixed z-[9999] w-64 px-3 py-2 text-xs text-slate-200 bg-slate-800 border border-slate-600 rounded-lg shadow-xl pointer-events-none -translate-x-1/2 -translate-y-full"
          style={{ top: pos.top, left: pos.left }}
        >
          {text}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
        </span>
      )}
    </>
  )
}

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

function AgentGraphSection() {
  const [graphConfig, setGraphConfig] = useState('baseline')

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-300">Agent Graph</span>
        <div className="flex gap-2">
          {CONFIGS.map(cfg => (
            <button
              key={cfg}
              onClick={() => setGraphConfig(cfg)}
              className={`px-3 py-1 text-xs rounded-md border transition-colors ${
                graphConfig === cfg
                  ? cfg === 'full' ? 'bg-indigo-600 border-indigo-500 text-white'
                    : cfg === 'no_reflection' ? 'bg-amber-700 border-amber-600 text-white'
                    : 'bg-slate-600 border-slate-500 text-white'
                  : 'bg-transparent border-slate-700 text-slate-400 hover:border-slate-500'
              }`}
            >
              {CONFIG_LABELS[cfg]}
            </button>
          ))}
        </div>
      </div>
      <AgentGraph activeConfig={graphConfig} />
    </div>
  )
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
      <h1 className="text-2xl font-bold mb-2">Benchmark Results</h1>
      <p className="text-slate-400 text-sm mb-6 leading-relaxed">
        An ablation study designed to isolate the effect of the reflection loop on onboarding quality. The central question: does making the agent score its own understanding and loop back actually produce better results, or is a single exploration pass enough?
      </p>

      {/* Methodology + Fine-tuning */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-slate-200 mb-3">Methodology</p>
          <ul className="space-y-1.5 text-xs text-slate-400 leading-relaxed">
            <li><span className="text-slate-300 font-medium">Repos:</span> 20 public repositories across Python, TypeScript, Go, Rust, Ruby, Java, PHP</li>
            <li><span className="text-slate-300 font-medium">Model:</span> GPT-4o-mini for exploration, GPT-4o for synthesis - same across all 3 configs</li>
            <li><span className="text-slate-300 font-medium">Judge:</span> GPT-4o rates each document 1-5 on clarity, completeness, and usefulness for a new developer. Prompt includes the repo file tree as context.</li>
            <li><span className="text-slate-300 font-medium">File Ref Accuracy:</span> fraction of file paths cited in the document that exist on disk via <code className="bg-slate-800 px-1 rounded">os.path.exists</code> - measures hallucination rate</li>
            <li><span className="text-slate-300 font-medium">Arch Coverage:</span> fraction of the top-8 most-imported modules that are mentioned in the document</li>
            <li><span className="text-slate-300 font-medium">Prompts:</span> fixed across all runs, no per-repo tuning</li>
          </ul>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <p className="text-sm font-semibold text-slate-200 mb-3">Fine-tuning</p>
          <p className="text-xs text-slate-400 leading-relaxed mb-3">
            The planner, reflector, and explorer nodes were fine-tuned on structured-output tasks where GPT-4o performed well but a smaller local model could not reliably produce the right JSON schema. The goal was not to make the model smarter - it was to make a 7B model reliably output the exact structured format these nodes require.
          </p>
          <ul className="space-y-1.5 text-xs text-slate-400">
            <li><span className="text-slate-300 font-medium">Base model:</span> Qwen2.5-7B-Instruct</li>
            <li><span className="text-slate-300 font-medium">Method:</span> LoRA fine-tuning via mlx-lm on Apple Silicon</li>
            <li><span className="text-slate-300 font-medium">Training data:</span> 1,834 (prompt, completion) pairs from 50 repos using GPT-4o as teacher</li>
            <li><span className="text-slate-300 font-medium">Tasks trained:</span> file selection (planner), understanding scoring (reflector), file summarization (explorer)</li>
            <li><span className="text-slate-300 font-medium">Best val loss:</span> 0.445 at iter 1,800</li>
            <li><span className="text-slate-300 font-medium">Serving:</span> Q4_K_M GGUF via Ollama - ~4.7GB, runs fully offline</li>
          </ul>
        </div>
      </div>

      {/* Phase 2: Knowledge Augmentation */}
      <div className="mb-8 bg-slate-900 border border-slate-700 rounded-xl p-5">
        <p className="text-sm font-semibold text-slate-200 mb-1">Phase 2: Knowledge Augmentation</p>
        <p className="text-xs text-slate-500 leading-relaxed mb-4">
          Built for Week 5-7 of the GenAI course. Grounds the agent in the repository's structure using hybrid retrieval, a Neo4j knowledge graph, and a custom LLM-as-a-Judge eval pipeline.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
            <p className="text-xs font-semibold text-indigo-300 mb-2">Week 5 - RAG 2.0</p>
            <ul className="space-y-1.5 text-xs text-slate-400 leading-relaxed">
              <li><span className="text-slate-300">Self-correcting loop:</span> the reflect node scores understanding and identifies gaps; those gaps become the retrieval query for the next planner call</li>
              <li><span className="text-slate-300">Hybrid search:</span> FAISS vector index (text-embedding-3-small) + keyword grep - both signals passed to the LLM for final file selection</li>
              <li><span className="text-slate-300">Index node:</span> embeds all repo files (path + 300 char preview) once per run, ~$0.001</li>
            </ul>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
            <p className="text-xs font-semibold text-emerald-300 mb-2">Week 6 - GraphRAG</p>
            <ul className="space-y-1.5 text-xs text-slate-400 leading-relaxed">
              <li><span className="text-slate-300">Neo4j schema:</span> <code className="bg-slate-700 px-1 rounded">(:File)</code> nodes + <code className="bg-slate-700 px-1 rounded">[:IMPORTS]</code> edges, scoped per run via <code className="bg-slate-700 px-1 rounded">run_id</code></li>
              <li><span className="text-slate-300">Centrality query:</span> in-degree count via Cypher replaces dict heuristic</li>
              <li><span className="text-slate-300">Frontier query:</span> 1-hop unvisited neighbors of visited files - files confirmed reachable from explored code</li>
            </ul>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
            <p className="text-xs font-semibold text-amber-300 mb-2">Week 7 - LLM-as-a-Judge</p>
            <ul className="space-y-1.5 text-xs text-slate-400 leading-relaxed">
              <li><span className="text-slate-300">GPT-4o judge:</span> scores each document 1-5 on clarity, completeness, and usefulness; always a different model than the one evaluated</li>
              <li><span className="text-slate-300">3 custom metrics:</span> architecture coverage, file ref accuracy, judge score - each measuring a distinct failure mode</li>
              <li><span className="text-slate-300">Ablation study:</span> 20 repos x 3 configs isolates the effect of each component</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Agent graph + config cards side by side */}
      <div className="flex gap-6 mb-10 items-stretch">
        {/* Graph - 55% */}
        <div className="w-[55%] shrink-0">
          <AgentGraphSection />
        </div>

        {/* Config description cards - 45%, space-between */}
        <div className="flex-1 flex flex-col justify-between">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
            <p className="text-sm font-semibold text-slate-300 mb-1">Baseline</p>
            <p className="text-xs text-slate-500 leading-relaxed">Clones the repo and reads only the README and dependency files, then synthesizes the onboarding document immediately - no file exploration at all. Establishes the floor for what the model can produce from surface-level information alone.</p>
          </div>
          <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4">
            <p className="text-sm font-semibold text-amber-300 mb-1">No Reflection</p>
            <p className="text-xs text-slate-500 leading-relaxed">Runs one full exploration cycle - reads files, builds an import graph, and summarizes key modules - then synthesizes directly without looping back. Shows how much a single pass of exploration improves over the baseline.</p>
          </div>
          <div className="bg-indigo-950/30 border border-indigo-800/40 rounded-xl p-4">
            <p className="text-sm font-semibold text-indigo-300 mb-1">Full</p>
            <p className="text-xs text-slate-500 leading-relaxed">Runs the complete reflection loop - after each exploration batch, the agent scores its own architectural understanding (0-1) and decides whether to explore more or synthesize. Loops up to 3 iterations until it reaches a score of 0.8 or higher.</p>
          </div>
        </div>
      </div>

      {/* Ablation charts */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {[
          { label: 'Architecture Coverage', metric: archCov, tooltip: METRIC_DESCRIPTIONS.ArchCov },
          { label: 'File Ref Accuracy', metric: fileRef, tooltip: METRIC_DESCRIPTIONS.FileRef },
          { label: 'Judge Score (normalized)', metric: { baseline: (judge.baseline ?? 0) / 5, no_reflection: (judge.no_reflection ?? 0) / 5, full: (judge.full ?? 0) / 5 }, tooltip: METRIC_DESCRIPTIONS.Judge },
        ].map(({ label, metric, tooltip }) => (
          <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
              <Tooltip text={tooltip}>
                <span className="cursor-help underline decoration-dotted decoration-slate-600">{label}</span>
              </Tooltip>
            </h3>
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
                  <th key={`${cfg}-arch`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">
                    <Tooltip text={METRIC_DESCRIPTIONS.ArchCov}>
                      <span className="cursor-help underline decoration-dotted decoration-slate-600">ArchCov</span>
                    </Tooltip>
                  </th>
                  <th key={`${cfg}-ref`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">
                    <Tooltip text={METRIC_DESCRIPTIONS.FileRef}>
                      <span className="cursor-help underline decoration-dotted decoration-slate-600">FileRef</span>
                    </Tooltip>
                  </th>
                  <th key={`${cfg}-judge`} className="px-4 py-2 text-xs text-slate-500 font-normal text-center">
                    <Tooltip text={METRIC_DESCRIPTIONS.Judge}>
                      <span className="cursor-help underline decoration-dotted decoration-slate-600">Judge</span>
                    </Tooltip>
                  </th>
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
