import React, { useState, useEffect } from 'react'
import { bringMeBack } from '../services/api_v4'

export default function BringMeBack({ sinceDays = 7 }) {
  const [briefing, setBriefing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchBriefing = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await bringMeBack(sinceDays)
      setBriefing(response.data.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBriefing()
  }, [sinceDays])

  if (loading) {
    return (
      <div className="bring-me-back loading">
        <div className="loading-spinner">⏳</div>
        <p>Preparing your briefing...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bring-me-back error">
        <p>Failed to generate briefing: {error}</p>
        <button onClick={fetchBriefing}>Retry</button>
      </div>
    )
  }

  if (!briefing) return null

  return (
    <div className="bring-me-back">
      <div className="briefing-header">
        <h2>🧠 Bring Me Back</h2>
        <button onClick={fetchBriefing} className="refresh-btn">🔄 Refresh</button>
      </div>

      <div className="greeting">
        <h3>{briefing.greeting}</h3>
        <p className="time-away">While you were away ({briefing.time_away?.duration || 'some time'})</p>
      </div>

      {/* New Knowledge */}
      {briefing.new_knowledge && briefing.new_knowledge.total > 0 && (
        <div className="section new-knowledge">
          <h4>📈 New Knowledge</h4>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{briefing.new_knowledge.nodes}</span>
              <span className="stat-label">Nodes</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{briefing.new_knowledge.relationships}</span>
              <span className="stat-label">Relationships</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{briefing.new_knowledge.assets}</span>
              <span className="stat-label">Assets</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{briefing.new_knowledge.events}</span>
              <span className="stat-label">Events</span>
            </div>
          </div>
        </div>
      )}

      {/* Active Projects */}
      {briefing.projects && briefing.projects.length > 0 && (
        <div className="section projects">
          <h4>🚀 Active Projects</h4>
          {briefing.projects.map(project => (
            <div key={project.id} className="project-card">
              <div className="project-header">
                <span className="project-title">{project.title}</span>
                <span className={`status-badge ${project.status}`}>{project.status}</span>
              </div>
              <div className="completeness-bar">
                <div 
                  className="completeness-fill" 
                  style={{ width: `${project.completeness}%` }}
                />
                <span className="completeness-text">{project.completeness}% complete</span>
              </div>
              {project.new_since_last_visit && Object.values(project.new_since_last_visit).some(v => v > 0) && (
                <div className="new-items">
                  <span>New since last visit: </span>
                  {Object.entries(project.new_since_last_visit)
                    .filter(([_, v]) => v > 0)
                    .map(([k, v]) => `${v} ${k}`)
                    .join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Unresolved Items */}
      {briefing.unresolved && (
        <div className="section unresolved">
          <h4>❓ Unresolved</h4>
          
          {briefing.unresolved.open_questions?.length > 0 && (
            <div className="unresolved-group">
              <p className="group-title">Open Questions ({briefing.unresolved.open_questions.length}):</p>
              <ul>
                {briefing.unresolved.open_questions.slice(0, 5).map(q => (
                  <li key={q.id}>{q.title}</li>
                ))}
              </ul>
            </div>
          )}
          
          {briefing.unresolved.recent_decisions?.length > 0 && (
            <div className="unresolved-group">
              <p className="group-title">Recent Decisions:</p>
              <ul>
                {briefing.unresolved.recent_decisions.map(d => (
                  <li key={d.id}>{d.title}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Current Focus */}
      {briefing.current_focus?.project && (
        <div className="section focus">
          <h4>🎯 Current Focus</h4>
          <div className="focus-card">
            <p className="focus-project">{briefing.current_focus.project.title}</p>
            {briefing.current_focus.current_goal && (
              <p className="focus-goal">Goal: {briefing.current_focus.current_goal}</p>
            )}
            {briefing.current_focus.summary && (
              <p className="focus-summary">{briefing.current_focus.summary}</p>
            )}
          </div>
        </div>
      )}

      {/* Blocked By */}
      {briefing.blocked_by && briefing.blocked_by.length > 0 && (
        <div className="section blocked">
          <h4>🚧 Blocked By</h4>
          {briefing.blocked_by.map(item => (
            <div key={item.id} className="blocked-item">
              <span className="blocked-title">{item.title}</span>
              <span className="blocked-reason">{item.reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* Suggested Next Steps */}
      {briefing.suggested_next_steps && briefing.suggested_next_steps.length > 0 && (
        <div className="section suggestions">
          <h4>💡 Suggested Next Steps</h4>
          {briefing.suggested_next_steps.map((suggestion, i) => (
            <div key={i} className={`suggestion-item ${suggestion.type}`}>
              <span className="suggestion-type">{suggestion.type}</span>
              <span className="suggestion-text">{suggestion.message}</span>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .bring-me-back {
          padding: 1.5rem;
          background: #f8fafc;
          border-radius: 12px;
          max-height: 80vh;
          overflow-y: auto;
        }
        
        .briefing-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        
        .briefing-header h2 {
          margin: 0;
          font-size: 1.5rem;
          color: #1e293b;
        }
        
        .refresh-btn {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
        }
        
        .refresh-btn:hover {
          background: #2563eb;
        }
        
        .greeting {
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid #e2e8f0;
        }
        
        .greeting h3 {
          margin: 0 0 0.5rem;
          font-size: 1.2rem;
          color: #1e293b;
        }
        
        .time-away {
          margin: 0;
          color: #64748b;
          font-size: 0.95rem;
        }
        
        .section {
          margin-bottom: 1.5rem;
        }
        
        .section h4 {
          margin: 0 0 0.75rem;
          font-size: 1rem;
          color: #475569;
        }
        
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
          gap: 0.75rem;
        }
        
        .stat-card {
          background: white;
          padding: 1rem;
          border-radius: 8px;
          text-align: center;
          border: 1px solid #e2e8f0;
        }
        
        .stat-value {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: #3b82f6;
        }
        
        .stat-label {
          font-size: 0.8rem;
          color: #64748b;
        }
        
        .project-card {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 0.75rem;
        }
        
        .project-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        
        .project-title {
          font-weight: 600;
          color: #1e293b;
        }
        
        .status-badge {
          font-size: 0.75rem;
          padding: 0.2rem 0.5rem;
          border-radius: 9999px;
          text-transform: uppercase;
          font-weight: 600;
        }
        
        .status-badge.active {
          background: #dcfce7;
          color: #166534;
        }
        
        .status-badge.draft {
          background: #fef3c7;
          color: #92400e;
        }
        
        .completeness-bar {
          position: relative;
          height: 8px;
          background: #e2e8f0;
          border-radius: 4px;
          overflow: hidden;
        }
        
        .completeness-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #22c55e);
          transition: width 0.3s;
        }
        
        .completeness-text {
          font-size: 0.8rem;
          color: #64748b;
          margin-top: 0.25rem;
          display: block;
        }
        
        .new-items {
          font-size: 0.8rem;
          color: #3b82f6;
          margin-top: 0.5rem;
        }
        
        .unresolved-group {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
        }
        
        .group-title {
          margin: 0 0 0.5rem;
          font-weight: 600;
          color: #475569;
          font-size: 0.9rem;
        }
        
        .unresolved-group ul {
          margin: 0;
          padding-left: 1.25rem;
        }
        
        .unresolved-group li {
          color: #64748b;
          font-size: 0.9rem;
          margin-bottom: 0.25rem;
        }
        
        .focus-card {
          background: white;
          border: 1px solid #3b82f6;
          border-radius: 8px;
          padding: 1rem;
        }
        
        .focus-project {
          font-weight: 600;
          font-size: 1.1rem;
          color: #1e293b;
          margin: 0 0 0.5rem;
        }
        
        .focus-goal {
          color: #3b82f6;
          margin: 0 0 0.5rem;
          font-size: 0.95rem;
        }
        
        .focus-summary {
          color: #64748b;
          margin: 0;
          font-size: 0.9rem;
        }
        
        .blocked-item {
          background: #fee2e2;
          border: 1px solid #fca5a5;
          border-radius: 6px;
          padding: 0.5rem 0.75rem;
          margin-bottom: 0.5rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .blocked-title {
          font-weight: 500;
          color: #991b1b;
        }
        
        .blocked-reason {
          font-size: 0.8rem;
          color: #dc2626;
        }
        
        .suggestion-item {
          background: white;
          border-left: 3px solid #3b82f6;
          border-radius: 0 6px 6px 0;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }
        
        .suggestion-type {
          font-size: 0.7rem;
          text-transform: uppercase;
          font-weight: 700;
          color: #3b82f6;
          min-width: 80px;
        }
        
        .suggestion-text {
          color: #475569;
          font-size: 0.9rem;
        }
        
        .loading {
          text-align: center;
          padding: 3rem;
        }
        
        .loading-spinner {
          font-size: 3rem;
          margin-bottom: 1rem;
        }
        
        .loading p {
          color: #64748b;
        }
      `}</style>
    </div>
  )
}
