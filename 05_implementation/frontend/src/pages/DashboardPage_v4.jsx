import React, { useState, useEffect } from 'react'
import { 
  getSidebar, getDashboard, bringMeBack,
  getPredictions, getPersonalModel, getOpportunities,
  getSecurityStats, getInfrastructureStatus, getRoadmapProgress,
  getLearningStats, getLearningSignals,
  getPendingTasks, getExecutionAuditLog,
  getConversationSessions,
  getConnectedSources, getPipelineRuns
} from '../services/api_v4'

function DashboardPage_v4({ onNavigateToChat, onNavigateToGraph }) {
  const [sidebar, setSidebar] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [briefing, setBriefing] = useState(null)
  const [predictions, setPredictions] = useState([])
  const [personalModel, setPersonalModel] = useState(null)
  const [opportunities, setOpportunities] = useState([])
  const [securityStats, setSecurityStats] = useState(null)
  const [infraStatus, setInfraStatus] = useState(null)
  const [roadmapProgress, setRoadmapProgress] = useState(null)
  const [learningStats, setLearningStats] = useState(null)
  const [learningSignals, setLearningSignals] = useState([])
  const [pendingTasks, setPendingTasks] = useState([])
  const [conversationSessions, setConversationSessions] = useState([])
  const [connectedSources, setConnectedSources] = useState([])
  const [pipelineRuns, setPipelineRuns] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000) // Auto-refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [sidebarRes, dashboardRes, briefingRes, predRes, pmRes, oppRes, secRes, infraRes, roadmapRes,
        learnRes, taskRes, sessRes, srcRes, runRes] = await Promise.all([
        getSidebar(),
        getDashboard(),
        bringMeBack(7).catch(() => ({ data: { data: null } })),
        getPredictions().catch(() => ({ data: { data: [] } })),
        getPersonalModel().catch(() => ({ data: { data: null } })),
        getOpportunities().catch(() => ({ data: { data: [] } })),
        getSecurityStats().catch(() => ({ data: { data: null } })),
        getInfrastructureStatus().catch(() => ({ data: { data: null } })),
        getRoadmapProgress().catch(() => ({ data: { data: null } })),
        getLearningStats().catch(() => ({ data: { data: null } })),
        getPendingTasks().catch(() => ({ data: { data: [] } })),
        getConversationSessions().catch(() => ({ data: { data: [] } })),
        getConnectedSources().catch(() => ({ data: { data: [] } })),
        getPipelineRuns().catch(() => ({ data: { data: [] } }))
      ])
      
      setSidebar(sidebarRes.data.data)
      setDashboard(dashboardRes.data.data)
      setBriefing(briefingRes.data.data)
      setPredictions(predRes.data.data || [])
      setPersonalModel(pmRes.data.data)
      setOpportunities(oppRes.data.data || [])
      setSecurityStats(secRes.data.data)
      setInfraStatus(infraRes.data.data)
      setRoadmapProgress(roadmapRes.data.data)
      setLearningStats(learnRes.data.data)
      setPendingTasks(taskRes.data.data || [])
      setConversationSessions(sessRes.data.data || [])
      setConnectedSources(srcRes.data.data || [])
      setPipelineRuns(runRes.data.data || [])
      setLastUpdated(new Date())
    } catch (e) {
      console.error('Dashboard load error:', e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="dashboard-v4 loading">
        <div className="loading-spinner">⏳</div>
        <p>Loading your world...</p>
      </div>
    )
  }

  const sections = sidebar?.sections || []
  const projects = sections.find(s => s.id === 'projects')?.items || []
  const people = sections.find(s => s.id === 'people')?.items || []
  const concepts = sections.find(s => s.id === 'concepts')?.items || []
  const stats = dashboard?.stats || { total_nodes: 0, total_edges: 0 }
  const recentNodes = dashboard?.recent_nodes || []

  const truncateText = (text, maxChars = 80) => {
    if (!text || text.length <= maxChars) return text || ''
    const cutAt = text.lastIndexOf(' ', maxChars)
    return (cutAt > 0 ? text.slice(0, cutAt) : text.slice(0, maxChars)) + '...'
  }

  return (
    <div className="dashboard-v4">
      {/* Header */}
      <div className="dashboard-header">
        <h1>🎯 Dashboard</h1>
        <p>Your command center. Everything at a glance.</p>
        {lastUpdated && (
          <p className="last-updated">Updated: {lastUpdated.toLocaleTimeString()}
            <button className="refresh-btn" onClick={loadData}>🔄 Refresh</button>
          </p>
        )}
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card clickable" onClick={() => onNavigateToGraph && onNavigateToGraph()}>
          <div className="stat-icon">🌐</div>
          <div className="stat-value">{stats.total_nodes}</div>
          <div className="stat-label">Knowledge Nodes</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔗</div>
          <div className="stat-value">{stats.total_edges}</div>
          <div className="stat-label">Relationships</div>
        </div>
        <div className="stat-card clickable" onClick={() => onNavigateToGraph && onNavigateToGraph()}>
          <div className="stat-icon">🚀</div>
          <div className="stat-value">{projects.length}</div>
          <div className="stat-label">Projects</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">👤</div>
          <div className="stat-value">{people.length}</div>
          <div className="stat-label">People</div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="dashboard-columns">
        <div className="column">
          {/* Projects */}
          <div className="section-card">
            <div className="section-header">
              <h3>🚀 Projects</h3>
              <span className="section-count">{projects.length}</span>
            </div>
            <div className="section-list">
              {projects.length === 0 && (
                <p className="empty-state">No projects yet. Add them in the Knowledge Graph.</p>
              )}
              {projects.map(project => (
                <div 
                  key={project.id} 
                  className="domain-item"
                  onClick={() => onNavigateToGraph && onNavigateToGraph(project.id)}
                >
                  <div className="domain-info">
                    <span className="domain-title">{project.title}</span>
                    <span className="domain-slug">{project.slug}</span>
                  </div>
                  <div className="completeness-bar">
                    <div 
                      className="completeness-fill"
                      style={{ width: `${project.completeness || 0}%` }}
                    />
                  </div>
                  <span className="completeness-text">{project.completeness || 0}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Concepts / Knowledge */}
          <div className="section-card">
            <div className="section-header">
              <h3>📚 Knowledge</h3>
              <span className="section-count">{concepts.length}</span>
            </div>
            <div className="section-list">
              {concepts.length === 0 && (
                <p className="empty-state">No concepts yet. Add them in the Knowledge Graph.</p>
              )}
              {concepts.map(concept => (
                <div 
                  key={concept.id} 
                  className="domain-item"
                  onClick={() => onNavigateToGraph && onNavigateToGraph(concept.id)}
                >
                  <div className="domain-info">
                    <span className="domain-title">{concept.title}</span>
                    <span className="domain-slug">{concept.slug}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="column">
          {/* Recent Activity */}
          <div className="section-card">
            <div className="section-header">
              <h3>🕐 Recent Activity</h3>
            </div>
            <div className="section-list">
              {recentNodes.length === 0 && (
                <p className="empty-state">No recent activity.</p>
              )}
              {recentNodes.slice(0, 10).map(node => (
                <div 
                  key={node.id} 
                  className="domain-item"
                  onClick={() => onNavigateToGraph && onNavigateToGraph(node.id)}
                >
                  <div className="domain-info">
                    <span className="domain-title">{node.title}</span>
                  </div>
                  <span className="activity-time">
                    {node.updated_at ? new Date(node.updated_at).toLocaleDateString() : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 13: Predictions */}
          <div className="section-card">
            <div className="section-header">
              <h3>🔮 Predictions</h3>
              <span className="section-count">{predictions.length}</span>
            </div>
            <div className="section-list">
              {predictions.length === 0 && (
                <p className="empty-state">No active predictions yet.</p>
              )}
              {predictions.map((pred, i) => (
                <div key={i} className="domain-item prediction-item">
                  <div className="domain-info">
                    <span className="domain-title">{truncateText(pred.description, 80) || 'Prediction'}</span>
                    <span className="domain-slug">{pred.type} · confidence: {Math.round(pred.confidence * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 14: Personal Model */}
          {personalModel && (
            <div className="section-card">
              <div className="section-header">
                <h3>👤 Personal Model</h3>
              </div>
              <div className="section-list">
                <div className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">Career: {personalModel.career?.current_role || 'Not set'}</span>
                    <span className="domain-slug">{personalModel.career?.verified_skills?.length || 0} verified skills</span>
                  </div>
                </div>
                <div className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{personalModel.knowledge_domains?.length || 0} Knowledge Domains</span>
                    <span className="domain-slug">{personalModel.projects?.length || 0} Projects tracked</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Phase 15: Opportunities */}
          <div className="section-card">
            <div className="section-header">
              <h3>🌟 Opportunities</h3>
              <span className="section-count">{opportunities.length}</span>
            </div>
            <div className="section-list">
              {opportunities.length === 0 && (
                <p className="empty-state">No opportunities detected yet.</p>
              )}
              {opportunities.map((opp, i) => (
                <div key={i} className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{opp.title}</span>
                    <span className="domain-slug">{opp.urgency} · {Math.round(opp.confidence * 100)}% confidence</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 09: Learning Engine */}
          {learningStats && (
            <div className="section-card">
              <div className="section-header">
                <h3>🧠 Learning</h3>
                <span className="section-count">{learningStats.total_signals}</span>
              </div>
              <div className="section-list">
                {Object.entries(learningStats.by_type || {}).map(([type, count]) => (
                  <div key={type} className="domain-item">
                    <div className="domain-info">
                      <span className="domain-title">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                      <span className="domain-slug">{count} signals</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 10: Execution Engine */}
          <div className="section-card">
            <div className="section-header">
              <h3>⚡ Tasks</h3>
              <span className="section-count">{pendingTasks.length}</span>
            </div>
            <div className="section-list">
              {pendingTasks.length === 0 && (
                <p className="empty-state">No pending tasks.</p>
              )}
              {pendingTasks.slice(0, 5).map(task => (
                <div key={task.id} className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{truncateText(task.description, 60)}</span>
                    <span className="domain-slug">{task.action_type} · {task.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 11: Conversation Sessions */}
          <div className="section-card">
            <div className="section-header">
              <h3>💬 Sessions</h3>
              <span className="section-count">{conversationSessions.length}</span>
            </div>
            <div className="section-list">
              {conversationSessions.length === 0 && (
                <p className="empty-state">No active sessions.</p>
              )}
              {conversationSessions.slice(0, 5).map(s => (
                <div key={s.id} className="domain-item" onClick={() => onNavigateToChat && onNavigateToChat()}>
                  <div className="domain-info">
                    <span className="domain-title">{s.title || 'Session'}</span>
                    <span className="domain-slug">{s.tokens} tokens · {s.attention_state}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 12: Knowledge Pipeline */}
          <div className="section-card">
            <div className="section-header">
              <h3>📥 Pipeline</h3>
              <span className="section-count">{pipelineRuns.length}</span>
            </div>
            <div className="section-list">
              {connectedSources.length > 0 && (
                <div className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{connectedSources.length} Connected Sources</span>
                    <span className="domain-slug">{connectedSources.map(s => s.source_type).join(', ')}</span>
                  </div>
                </div>
              )}
              {pipelineRuns.length === 0 && connectedSources.length === 0 && (
                <p className="empty-state">No pipeline runs yet.</p>
              )}
              {pipelineRuns.slice(0, 3).map(r => (
                <div key={r.id} className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{r.source_type}</span>
                    <span className="domain-slug">{r.status} · {r.blocks} blocks</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Phase 17: Security */}
          {securityStats && (
            <div className="section-card">
              <div className="section-header">
                <h3>🔒 Security</h3>
              </div>
              <div className="section-list">
                <div className="domain-item">
                  <div className="domain-info">
                    <span className="domain-title">{securityStats.total_classifications} Classifications</span>
                    <span className="domain-slug">{securityStats.encryption_required} encrypted · {securityStats.audit_entries} audit entries</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Phase 18: Infrastructure */}
          {infraStatus && (
            <div className="section-card">
              <div className="section-header">
                <h3>🏗️ Infrastructure</h3>
              </div>
              <div className="infra-grid">
                {Object.entries(infraStatus).filter(([k]) => k !== 'note').map(([service, status]) => (
                  <div key={service} className="infra-item">
                    <span className={`infra-status ${String(status).includes('configured') ? 'ok' : 'warn'}`}></span>
                    <span className="infra-name">{service}</span>
                    <span className="infra-value">{status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .dashboard-v4 {
          padding: 1.5rem;
          overflow-y: auto;
          height: 100%;
          background: #f8fafc;
        }
        
        .dashboard-header {
          margin-bottom: 1.5rem;
        }
        
        .dashboard-header h1 {
          margin: 0;
          font-size: 1.5rem;
          color: #1e293b;
        }
        
        .dashboard-header p {
          margin: 0.25rem 0 0;
          color: #64748b;
        }
        
        .last-updated {
          font-size: 0.8rem;
          color: #94a3b8;
          margin-top: 0.5rem;
        }
        
        .refresh-btn {
          margin-left: 0.5rem;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 0.9rem;
        }
        
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .stat-card {
          background: white;
          padding: 1.25rem;
          border-radius: 12px;
          border: 1px solid #e2e8f0;
          text-align: center;
          transition: all 0.15s;
        }
        
        .stat-card.clickable {
          cursor: pointer;
        }
        
        .stat-card.clickable:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
          border-color: #3b82f6;
        }
        
        .stat-icon {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }
        
        .stat-value {
          font-size: 1.75rem;
          font-weight: 700;
          color: #1e293b;
        }
        
        .stat-label {
          font-size: 0.8rem;
          color: #64748b;
          margin-top: 0.25rem;
        }
        
        .dashboard-columns {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1rem;
        }
        
        .section-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 1rem;
        }
        
        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }
        
        .section-header h3 {
          margin: 0;
          font-size: 1rem;
          color: #1e293b;
        }
        
        .section-count {
          font-size: 0.8rem;
          color: #64748b;
          background: #f1f5f9;
          padding: 0.2rem 0.6rem;
          border-radius: 9999px;
        }
        
        .section-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        .empty-state {
          color: #94a3b8;
          font-size: 0.9rem;
          text-align: center;
          padding: 1rem;
        }
        
        .domain-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.6rem 0.75rem;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.15s;
        }
        
        .domain-item:hover {
          background: #f8fafc;
        }
        
        .domain-info {
          flex: 1;
          min-width: 0;
        }
        
        .domain-title {
          display: block;
          font-size: 0.9rem;
          font-weight: 500;
          color: #1e293b;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .domain-slug {
          display: block;
          font-size: 0.75rem;
          color: #94a3b8;
        }
        
        .completeness-bar {
          width: 60px;
          height: 6px;
          background: #e2e8f0;
          border-radius: 3px;
          overflow: hidden;
        }
        
        .completeness-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #22c55e);
          border-radius: 3px;
          transition: width 0.3s;
        }
        
        .completeness-text {
          font-size: 0.75rem;
          color: #64748b;
          min-width: 32px;
          text-align: right;
        }
        
        .activity-time {
          font-size: 0.75rem;
          color: #94a3b8;
          white-space: nowrap;
        }
        
        .quick-actions {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 0.75rem;
        }
        
        .action-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1rem;
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.15s;
          border: none;
          font-family: inherit;
        }
        
        .action-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        
        .action-card.chat:hover { background: #eff6ff; border-color: #3b82f6; }
        .action-card.graph:hover { background: #f0fdf4; border-color: #22c55e; }
        
        .action-icon {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }
        
        .action-title {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1e293b;
        }
        
        .action-desc {
          font-size: 0.75rem;
          color: #64748b;
          margin-top: 0.2rem;
        }
        
        .loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem;
        }
        
        .loading-spinner {
          font-size: 2rem;
          margin-bottom: 1rem;
        }
        
        .loading p {
          color: #64748b;
        }
      `}</style>
    </div>
  )
}

export default DashboardPage_v4
