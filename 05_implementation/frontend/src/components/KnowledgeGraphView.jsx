import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { getFullGraph, getSubgraph } from '../services/api_v4'

const LAYER_COLORS = {
  project: '#3b82f6',
  knowledge: '#8b5cf6',
  life: '#22c55e',
  system: '#94a3b8',
  general: '#f59e0b',
}

const TYPE_COLORS = {
  project: '#3b82f6',
  concept: '#8b5cf6',
  person: '#ec4899',
  decision: '#f59e0b',
  insight: '#14b8a6',
  task: '#ef4444',
  question: '#a855f7',
}

function nodeColor(node) {
  if (node.layer && LAYER_COLORS[node.layer]) return LAYER_COLORS[node.layer]
  if (node.type && TYPE_COLORS[node.type]) return TYPE_COLORS[node.type]
  return '#64748b'
}

/**
 * Obsidian-style force-directed knowledge graph.
 */
export default function KnowledgeGraphView({
  activeNodeId = null,
  onNodeSelect = null,
  focusNodeId = null,
}) {
  const fgRef = useRef(null)
  const containerRef = useRef(null)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [hoverNode, setHoverNode] = useState(null)
  const [dims, setDims] = useState({ width: 600, height: 500 })
  const [mode, setMode] = useState('full') // 'full' | 'local'

  // Resize observer
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => {
      const rect = el.getBoundingClientRect()
      setDims({
        width: Math.max(300, rect.width),
        height: Math.max(300, rect.height),
      })
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let data
      if (mode === 'local' && (focusNodeId || activeNodeId)) {
        const seed = focusNodeId || activeNodeId
        const res = await getSubgraph(seed, 2)
        data = res.data?.data || res.data
      } else {
        const res = await getFullGraph(200)
        data = res.data?.data || res.data
      }

      const nodes = (data?.nodes || []).map(n => ({
        id: n.id,
        name: n.title || n.slug || n.id,
        title: n.title || n.slug || 'Untitled',
        type: n.type || 'unknown',
        layer: n.layer || 'project',
        val: 1,
      }))

      const nodeIdSet = new Set(nodes.map(n => n.id))
      const links = (data?.edges || [])
        .filter(e => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
        .map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.relationship_display || e.relationship_type || '',
          confidence: e.confidence || 1,
        }))

      setGraphData({ nodes, links })
    } catch (err) {
      console.error('[KnowledgeGraphView]', err)
      setError(err.message || 'Failed to load graph')
      setGraphData({ nodes: [], links: [] })
    } finally {
      setLoading(false)
    }
  }, [mode, focusNodeId, activeNodeId])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  // Center on active node when it changes
  useEffect(() => {
    if (!activeNodeId || !fgRef.current || !graphData.nodes.length) return
    const node = graphData.nodes.find(n => n.id === activeNodeId)
    if (node && typeof node.x === 'number') {
      fgRef.current.centerAt(node.x, node.y, 600)
      fgRef.current.zoom(2.5, 600)
    }
  }, [activeNodeId, graphData.nodes])

  const paintNode = useCallback((node, ctx, globalScale) => {
    const label = node.title || node.name || ''
    const fontSize = Math.max(10 / globalScale, 2.5)
    const isActive = node.id === activeNodeId
    const isHover = hoverNode && hoverNode.id === node.id
    const radius = isActive || isHover ? 7 : 5
    const color = nodeColor(node)

    // Glow for active/hover
    if (isActive || isHover) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI)
      ctx.fillStyle = color + '55'
      ctx.fill()
    }

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()
    if (isActive) {
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.5 / globalScale
      ctx.stroke()
    }

    // Label
    if (globalScale > 0.6 || isActive || isHover) {
      ctx.font = `${fontSize}px Sans-Serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillStyle = 'rgba(226, 232, 240, 0.9)'
      const short = label.length > 28 ? label.slice(0, 26) + '…' : label
      ctx.fillText(short, node.x, node.y + radius + 2)
    }
  }, [activeNodeId, hoverNode])

  const handleNodeClick = useCallback((node) => {
    if (onNodeSelect) onNodeSelect(node.id)
  }, [onNodeSelect])

  const legend = useMemo(() => ([
    { key: 'project', label: 'Project', color: LAYER_COLORS.project },
    { key: 'knowledge', label: 'Knowledge', color: LAYER_COLORS.knowledge },
    { key: 'life', label: 'Life', color: LAYER_COLORS.life },
    { key: 'system', label: 'System', color: LAYER_COLORS.system },
  ]), [])

  return (
    <div className="kg-graph-root" ref={containerRef}>
      <div className="kg-graph-toolbar">
        <div className="kg-graph-toolbar-left">
          <button
            className={`kg-mode-btn ${mode === 'full' ? 'active' : ''}`}
            onClick={() => setMode('full')}
            title="Show entire knowledge graph"
          >
            Global
          </button>
          <button
            className={`kg-mode-btn ${mode === 'local' ? 'active' : ''}`}
            onClick={() => setMode('local')}
            disabled={!activeNodeId}
            title="Show neighborhood of selected node"
          >
            Local
          </button>
          <button className="kg-mode-btn" onClick={loadGraph} title="Refresh">
            Refresh
          </button>
        </div>
        <div className="kg-graph-stats">
          {loading ? 'Loading…' : `${graphData.nodes.length} nodes · ${graphData.links.length} links`}
        </div>
      </div>

      {error && (
        <div className="kg-graph-error">{error}</div>
      )}

      {!loading && graphData.nodes.length === 0 && !error && (
        <div className="kg-graph-empty">
          No knowledge nodes to display yet. Add concepts in chat or upload documents.
        </div>
      )}

      {!loading && graphData.nodes.length > 0 && (
        <ForceGraph2D
          ref={fgRef}
          width={dims.width}
          height={dims.height - 44}
          graphData={graphData}
          backgroundColor="#1a1a2e"
          nodeId="id"
          nodeLabel={n => n.title}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.beginPath()
            ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI)
            ctx.fillStyle = color
            ctx.fill()
          }}
          linkColor={() => 'rgba(255,255,255,0.18)'}
          linkWidth={l => (l.confidence || 1) * 1.2}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleColor={() => 'rgba(148,163,184,0.6)'}
          onNodeClick={handleNodeClick}
          onNodeHover={setHoverNode}
          cooldownTicks={80}
          d3AlphaDecay={0.04}
          d3VelocityDecay={0.3}
        />
      )}

      <div className="kg-graph-legend">
        {legend.map(item => (
          <span key={item.key} className="kg-legend-item">
            <span className="kg-legend-dot" style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  )
}
