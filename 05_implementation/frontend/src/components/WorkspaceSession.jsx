import React, { useState, useEffect } from 'react'
import { getDashboard } from '../services/api_v4'

export default function WorkspaceSession({ activeNodeId }) {
  const [session, setSession] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [activeNodeId])

  const loadDashboard = async () => {
    try {
      const response = await getDashboard()
      setStats(response.data.data)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  // Generate session from current state
  useEffect(() => {
    if (stats) {
      const generatedSession = {
        project: stats.recent_nodes?.[0] || null,
        open_nodes: stats.recent_nodes?.slice(0, 5) || [],
        stats: stats.stats,
        last_active: new Date().toISOString()
      }
      setSession(generatedSession)
    }
  }, [stats])

  if (loading) {
    return (
      <div className="workspace-session loading">
        <p>Loading workspace...</p>
      </div>
    )
  }

  return (
    <div className="workspace-session">
      <div className="session-header">
        <h3>🎯 Workspace</h3>
      </div>

      {/* Stats Overview */}
      {stats?.stats && (
        <div className="stats-overview">
          <div className="stat-row">
            <span className="stat-name">Knowledge Nodes</span>
            <span className="stat-value">{stats.stats.total_nodes}</span>
          </div>
          <div className="stat-row">
            <span className="stat-name">Relationships</span>
            <span className="stat-value">{stats.stats.total_edges}</span>
          </div>
        </div>
      )}

      {/* Current Context */}
      {session?.project && (
        <div className="context-section">
          <h4>Current Focus</h4>
          <div className="focus-card">
            <p className="focus-title">{session.project.title}</p>
            <p className="focus-meta">Updated {new Date(session.project.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      )}

      {/* Recent Nodes */}
      {session?.open_nodes && session.open_nodes.length > 0 && (
        <div className="context-section">
          <h4>Recent Activity</h4>
          <div className="recent-list">
            {session.open_nodes.map(node => (
              <div key={node.id} className="recent-item">
                <span className="recent-title">{node.title}</span>
                <span className="recent-time">
                  {node.updated_at ? new Date(node.updated_at).toLocaleDateString() : 'Unknown'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="context-section">
        <h4>Quick Actions</h4>
        <div className="quick-actions">
          <button className="action-btn primary">
            + New Knowledge
          </button>
          <button className="action-btn">
            📤 Import Data
          </button>
          <button className="action-btn">
            🔍 Search Graph
          </button>
        </div>
      </div>

      <style jsx>{`
        .workspace-session {
          padding: 1rem;
          height: 100%;
          overflow-y: auto;
        }
        
        .session-header {
          margin-bottom: 1rem;
        }
        
        .session-header h3 {
          margin: 0;
          font-size: 1.1rem;
          color: #1e293b;
        }
        
        .stats-overview {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 0.75rem;
          margin-bottom: 1rem;
        }
        
        .stat-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 0;
          border-bottom: 1px solid #f1f5f9;
        }
        
        .stat-row:last-child {
          border-bottom: none;
        }
        
        .stat-name {
          font-size: 0.85rem;
          color: #64748b;
        }
        
        .stat-value {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1e293b;
        }
        
        .context-section {
          margin-bottom: 1.25rem;
        }
        
        .context-section h4 {
          margin: 0 0 0.5rem;
          font-size: 0.8rem;
          text-transform: uppercase;
          color: #94a3b8;
          font-weight: 600;
          letter-spacing: 0.05em;
        }
        
        .focus-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 0.75rem;
        }
        
        .focus-title {
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 0.25rem;
          font-size: 0.95rem;
        }
        
        .focus-meta {
          font-size: 0.8rem;
          color: #94a3b8;
          margin: 0;
        }
        
        .recent-list {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          overflow: hidden;
        }
        
        .recent-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.6rem 0.75rem;
          border-bottom: 1px solid #f1f5f9;
        }
        
        .recent-item:last-child {
          border-bottom: none;
        }
        
        .recent-title {
          font-size: 0.85rem;
          color: #475569;
          font-weight: 500;
        }
        
        .recent-time {
          font-size: 0.75rem;
          color: #94a3b8;
        }
        
        .quick-actions {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        .action-btn {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          padding: 0.6rem 0.75rem;
          font-size: 0.85rem;
          color: #475569;
          cursor: pointer;
          text-align: left;
          transition: all 0.15s;
        }
        
        .action-btn:hover {
          background: #f8fafc;
          border-color: #cbd5e1;
        }
        
        .action-btn.primary {
          background: #3b82f6;
          color: white;
          border-color: #3b82f6;
        }
        
        .action-btn.primary:hover {
          background: #2563eb;
        }
        
        .loading {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }
        
        .loading p {
          color: #94a3b8;
          font-size: 0.9rem;
        }
      `}</style>
    </div>
  )
}
