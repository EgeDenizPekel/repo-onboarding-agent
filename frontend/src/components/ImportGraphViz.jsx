/**
 * ImportGraphViz - Visualizes the file import graph built during agent exploration.
 *
 * Nodes: every file that appears in the import graph (explored or referenced).
 * Edges: A -> B if file A imports file B.
 * Layout: concentric rings ordered by in-degree (most-imported files in center).
 * Colors: indigo = explored by agent, slate = referenced but not visited (frontier stubs).
 * Size: node radius scales with in-degree (more imports = larger node).
 */

export default function ImportGraphViz({ importGraph }) {
  if (!importGraph || Object.keys(importGraph).length === 0) return null

  const W = 440, H = 440, CX = 220, CY = 220

  // Build full node set: explored files + their import targets
  const explored = new Set(Object.keys(importGraph))
  const nodeSet = new Set(explored)
  for (const targets of Object.values(importGraph)) {
    for (const t of targets) nodeSet.add(t)
  }

  // In-degree: how many explored files import each node
  const inDegree = {}
  for (const node of nodeSet) inDegree[node] = 0
  for (const targets of Object.values(importGraph)) {
    for (const t of targets) {
      inDegree[t] = (inDegree[t] || 0) + 1
    }
  }

  // Sort by in-degree desc, cap at 40 nodes for readability
  const nodes = [...nodeSet]
    .sort((a, b) => (inDegree[b] || 0) - (inDegree[a] || 0))
    .slice(0, 40)

  const nodeSet40 = new Set(nodes)

  // Concentric ring layout based on in-degree rank
  const rings = [
    { start: 0,  end: Math.min(3, nodes.length),  r: 65  },
    { start: 3,  end: Math.min(11, nodes.length), r: 130 },
    { start: 11, end: nodes.length,               r: 190 },
  ]

  const positions = {}
  for (const ring of rings) {
    const count = ring.end - ring.start
    if (count <= 0) continue
    for (let i = ring.start; i < ring.end; i++) {
      const angle = (2 * Math.PI * (i - ring.start)) / count - Math.PI / 2
      positions[nodes[i]] = {
        x: CX + ring.r * Math.cos(angle),
        y: CY + ring.r * Math.sin(angle),
      }
    }
  }

  // Edges - only between nodes that made the cap
  const edges = []
  for (const [src, targets] of Object.entries(importGraph)) {
    if (!nodeSet40.has(src)) continue
    for (const tgt of targets) {
      if (nodeSet40.has(tgt) && src !== tgt) {
        edges.push({ src, tgt })
      }
    }
  }

  function shortName(path) {
    const parts = path.split('/')
    return parts[parts.length - 1]
  }

  return (
    <div>
      <p className="text-xs font-semibold text-slate-400 mb-1">
        Import Graph
        <span className="font-normal text-slate-600 ml-2">
          {nodes.length} files, {edges.length} import edges
        </span>
      </p>
      <div className="rounded-lg overflow-hidden border border-slate-800">
        <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="bg-slate-950/60">
          {/* Edges */}
          {edges.map(({ src, tgt }, i) => {
            const s = positions[src]
            const t = positions[tgt]
            if (!s || !t) return null
            return (
              <line
                key={i}
                x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke="#1e293b" strokeWidth="1" strokeOpacity="0.9"
              />
            )
          })}

          {/* Nodes */}
          {nodes.map(node => {
            const pos = positions[node]
            if (!pos) return null
            const isExplored = explored.has(node)
            const deg = inDegree[node] || 0
            const r = 4 + Math.min(deg * 2, 10)
            const label = shortName(node)
            return (
              <g key={node}>
                <circle
                  cx={pos.x} cy={pos.y} r={r}
                  fill={isExplored ? 'rgba(79,70,229,0.75)' : 'rgba(51,65,85,0.7)'}
                  stroke={isExplored ? '#818cf8' : '#475569'}
                  strokeWidth="1"
                />
                <text
                  x={pos.x}
                  y={pos.y - r - 3}
                  textAnchor="middle"
                  fontSize="6.5"
                  fill={isExplored ? '#c7d2fe' : '#64748b'}
                >
                  {label.length > 18 ? label.slice(0, 16) + '..' : label}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div className="flex gap-5 mt-2">
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-indigo-600/75 border border-indigo-400 shrink-0" />
          <span className="text-xs text-slate-500">Explored by agent</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700/70 border border-slate-500 shrink-0" />
          <span className="text-xs text-slate-500">Referenced (not visited)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-px bg-slate-700 shrink-0" />
          <span className="text-xs text-slate-500">Imports</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">Node size = in-degree</span>
        </div>
      </div>
    </div>
  )
}
