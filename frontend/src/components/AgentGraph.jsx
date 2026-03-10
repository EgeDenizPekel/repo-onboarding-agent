import { useState } from 'react'

const CONFIG_ACTIVE_NODES = {
  baseline:      new Set(['clone_repo', 'initialize', 'synthesize', 'validate', 'refine']),
  no_reflection: new Set(['clone_repo', 'initialize', 'planner', 'explorer', 'synthesize', 'validate', 'refine']),
  full:          new Set(['clone_repo', 'initialize', 'planner', 'explorer', 'reflector', 'synthesize', 'validate', 'refine']),
}

const NODE_DESCRIPTIONS = {
  clone_repo:  'Clones the GitHub repository locally via GitPython. Extracts the full file tree, detects the primary language and framework, and sets up the working directory for the rest of the agent.',
  initialize:  'Reads the README and dependency files (package.json, pyproject.toml, go.mod, etc.) to understand the project at a high level. Seeds the initial exploration queue with entry point candidates.',
  planner:     'Uses an LLM to decide which 3-5 files to read next. Prioritizes entry points, files frequently imported by already-visited files, and gaps identified in the last reflection cycle.',
  explorer:    'Reads each queued file (capped at 4,000 tokens), generates a concise summary with an LLM, and extracts import statements to build the cross-file import graph.',
  reflector:   "Scores the agent's current architectural understanding from 0.0 to 1.0. Identifies what is understood well and what gaps remain. If score < 0.8 and iterations remain, loops back to the planner.",
  synthesize:  'Generates the full developer onboarding document from all accumulated state - file summaries, import graph, entry points, architecture notes, and reflection history.',
  validate:    'Deterministically checks every file path referenced in the document using os.path.exists. No LLM involved - this is a hard correctness check to catch hallucinated file references.',
  refine:      'Re-runs synthesis with the list of broken file references explicitly flagged, asking the LLM to correct or remove them from the document.',
}

const NODE_LABELS = {
  clone_repo: 'Clone Repo',
  initialize: 'Initialize',
  planner:    'Planner',
  explorer:   'Explorer',
  reflector:  'Reflector',
  synthesize: 'Synthesize',
  validate:   'Validate',
  refine:     'Refine',
}

// Layout constants
const NODE_W = 120
const NODE_H = 36
const CX = 160      // center x of main column
const GAP = 56      // vertical gap between node centers
const LOOP_X = 270  // x for the loop-back line on the right

const NODES = [
  { id: 'clone_repo', y: 0   },
  { id: 'initialize', y: 1   },
  { id: 'planner',    y: 2   },
  { id: 'explorer',   y: 3   },
  { id: 'reflector',  y: 4   },
  { id: 'synthesize', y: 5.8 },
  { id: 'validate',   y: 6.8 },
  { id: 'refine',     y: 7.8 },
]

function nodeY(slot) { return 24 + slot * GAP }
function nodeCY(slot) { return nodeY(slot) + NODE_H / 2 }

export default function AgentGraph({ activeConfig }) {
  const active = CONFIG_ACTIVE_NODES[activeConfig] ?? CONFIG_ACTIVE_NODES.full
  const [tooltip, setTooltip] = useState(null)

  const SVG_H = nodeY(7.8) + NODE_H + 24
  const SVG_W = 340

  // edge helpers
  function edgeColor(a, b) { return active.has(a) && active.has(b) ? '#6366f1' : '#334155' }
  function arrowId(a, b) { return `arrow-${a}-${b}` }

  const mainEdges = [
    ['clone_repo', 'initialize'],
    ['initialize', 'planner'],
    ['planner',    'explorer'],
    ['explorer',   'reflector'],
    ['synthesize', 'validate'],
    ['validate',   'refine'],
  ]

  // reflector -> synthesize (skips a slot, draw with offset label)
  const reflSynthColor = edgeColor('reflector', 'synthesize')
  const reflPlanColor  = edgeColor('reflector', 'planner')

  function handleMouseEnter(e, id) {
    const TOOLTIP_W = 288
    const x = Math.min(Math.max(e.clientX, TOOLTIP_W / 2 + 8), window.innerWidth - TOOLTIP_W / 2 - 8)
    setTooltip({ id, x, y: e.clientY })
  }

  return (
    <div className="relative rounded-xl border border-slate-800 bg-slate-950 overflow-visible">
      <svg
        width="100%"
        height={SVG_H}
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* one arrowhead marker per edge color */}
          <marker id="arrow-active" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#6366f1" />
          </marker>
          <marker id="arrow-inactive" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#334155" />
          </marker>
        </defs>

        {/* Main straight edges */}
        {mainEdges.map(([a, b]) => {
          const color = edgeColor(a, b)
          const aNode = NODES.find(n => n.id === a)
          const bNode = NODES.find(n => n.id === b)
          const y1 = nodeY(aNode.y) + NODE_H
          const y2 = nodeY(bNode.y)
          const isActive = active.has(a) && active.has(b)
          return (
            <line
              key={`${a}-${b}`}
              x1={CX} y1={y1} x2={CX} y2={y2 - 4}
              stroke={color} strokeWidth="1.5"
              markerEnd={`url(#arrow-${isActive ? 'active' : 'inactive'})`}
            />
          )
        })}

        {/* reflector -> synthesize (longer gap, with label) */}
        {(() => {
          const rY = nodeY(4) + NODE_H
          const sY = nodeY(5.8) - 4
          const isActive = active.has('reflector') && active.has('synthesize')
          const midY = (rY + sY) / 2
          return (
            <>
              <line x1={CX} y1={rY} x2={CX} y2={sY}
                stroke={reflSynthColor} strokeWidth="1.5"
                markerEnd={`url(#arrow-${isActive ? 'active' : 'inactive'})`}
              />
              <rect x={CX - 62} y={midY - 9} width={124} height={16} rx="3"
                fill="#0f172a" stroke={reflSynthColor} strokeWidth="0.5" opacity="0.9"
              />
              <text x={CX} y={midY + 4} textAnchor="middle"
                fontSize="8" fill={isActive ? '#818cf8' : '#475569'}
              >
                score &gt;= 0.8 or max iters
              </text>
            </>
          )
        })()}

        {/* reflector -> planner loop-back (right side) */}
        {(() => {
          const rSlot = NODES.find(n => n.id === 'reflector').y
          const pSlot = NODES.find(n => n.id === 'planner').y
          const rCY = nodeCY(rSlot)
          const pCY = nodeCY(pSlot)
          const rRight = CX + NODE_W / 2
          const pRight = CX + NODE_W / 2
          const isActive = active.has('reflector') && active.has('planner')
          const color = reflPlanColor
          const lx = LOOP_X + 20
          return (
            <>
              <path
                d={`M ${rRight} ${rCY} H ${lx} V ${pCY} H ${pRight + 4}`}
                fill="none" stroke={color} strokeWidth="1.5"
                markerEnd={`url(#arrow-${isActive ? 'active' : 'inactive'})`}
              />
              <rect x={lx + 4} y={(rCY + pCY) / 2 - 9} width={60} height={16} rx="3"
                fill="#0f172a" stroke={color} strokeWidth="0.5" opacity="0.9"
              />
              <text x={lx + 34} y={(rCY + pCY) / 2 + 4} textAnchor="middle"
                fontSize="8" fill={isActive ? '#818cf8' : '#475569'}
              >
                score &lt; 0.8
              </text>
            </>
          )
        })()}

        {/* Nodes */}
        {NODES.map(({ id, y }) => {
          const isActive = active.has(id)
          const x = CX - NODE_W / 2
          const ny = nodeY(y)
          return (
            <g key={id}
              onMouseEnter={e => handleMouseEnter(e, id)}
              onMouseMove={e => handleMouseEnter(e, id)}
              onMouseLeave={() => setTooltip(null)}
              style={{ cursor: 'default' }}
            >
              <rect
                x={x} y={ny} width={NODE_W} height={NODE_H} rx="8"
                fill={isActive ? 'rgba(67,56,202,0.25)' : 'rgba(30,41,59,0.4)'}
                stroke={isActive ? '#6366f1' : '#334155'}
                strokeWidth="1.5"
              />
              <text
                x={CX} y={ny + NODE_H / 2 + 4}
                textAnchor="middle"
                fontSize="11"
                fontWeight="500"
                fill={isActive ? '#c7d2fe' : '#64748b'}
              >
                {NODE_LABELS[id]}
              </text>
            </g>
          )
        })}
      </svg>

      {tooltip && (
        <div
          className="fixed z-[9999] w-72 px-3 py-2.5 text-xs text-slate-200 bg-slate-800 border border-slate-600 rounded-lg shadow-xl pointer-events-none leading-relaxed"
          style={{ top: tooltip.y - 12, left: tooltip.x, transform: 'translate(-50%, -100%)' }}
        >
          <p className="font-semibold text-white mb-1">{NODE_LABELS[tooltip.id]}</p>
          {NODE_DESCRIPTIONS[tooltip.id]}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
        </div>
      )}
    </div>
  )
}
