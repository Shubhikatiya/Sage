import React, { useState, useEffect } from 'react'
import { getDashboard } from '../services/api_v4'

function WorkspaceContext({ activeNodeId }) {
  const [dashboard, setDashboard] = useState(null)

  useEffect(() => {
    fetchDashboard()
  }, [])

  const fetchDashboard = async () => {
    try {
      const r = await getDashboard()
      if (r.data.success) {
        setDashboard(r.data.data)
      }
    } catch (e) {
      console.error(e)
    }
  }

  if (!dashboard) {
    return (
      <div className="w-80 bg-slate-50 border-l border-slate-200 p-4">
        <div className="text-sm text-slate-400">Loading workspace context...</div>
      </div>
    )
  }

  return (
    <div className="w-80 bg-slate-50 border-l border-slate-200 flex flex-col h-full overflow-y-auto">
      {/* Workspace Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="font-semibold text-slate-800">{dashboard.workspace.name}</div>
        <div className="text-xs text-slate-500 mt-1">Founder Knowledge Base</div>
      </div>

      {/* Stats */}
      <div className="p-4 grid grid-cols-2 gap-3">
        <StatBox label="Nodes" value={dashboard.stats.total_nodes} color="blue" />
        <StatBox label="Relationships" value={dashboard.stats.total_edges} color="purple" />
      </div>

      {/* Recent Activity */}
      <div className="px-4 pb-4">
        <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Recently Updated</div>
        <div className="space-y-2">
          {dashboard.recent_nodes.map((node) => (
            <div key={node.id} className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200">
              <div className="flex-1">
                <div className="text-sm font-medium text-slate-700 truncate">{node.title}</div>
                <div className="text-xs text-slate-400">{node.updated_at ? new Date(node.updated_at).toLocaleDateString() : 'Unknown'}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="px-4 pb-4">
        <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Quick Actions</div>
        <div className="space-y-2">
          <button className="w-full text-left px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            ➕ Create Knowledge Object
          </button>
          <button className="w-full text-left px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            🔗 Add Relationship
          </button>
          <button className="w-full text-left px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            📅 Add Timeline Event
          </button>
          <button className="w-full text-left px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            📊 Take State Snapshot
          </button>
        </div>
      </div>

      {/* Active Node Context */}
      {activeNodeId && (
        <div className="px-4 pb-4">
          <div className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-3">Current Context</div>
          <div className="p-3 bg-sage-50 border border-sage-200 rounded-lg">
            <div className="text-sm font-medium text-sage-800">Viewing Node</div>
            <div className="text-xs text-sage-600 mt-1">ID: {activeNodeId.slice(0, 8)}...</div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatBox({ label, value, color }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    purple: 'bg-purple-50 text-purple-700',
    green: 'bg-green-50 text-green-700',
    orange: 'bg-orange-50 text-orange-700',
  }
  
  return (
    <div className={`p-3 rounded-lg ${colors[color] || colors.blue}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-70">{label}</div>
    </div>
  )
}

export default WorkspaceContext
