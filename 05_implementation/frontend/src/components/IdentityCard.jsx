import React, { useState, useEffect } from 'react'
import { getIdentityCard, getNeighbors } from '../services/api_v4'

function IdentityCard({ nodeId }) {
  const [identity, setIdentity] = useState(null)
  const [neighbors, setNeighbors] = useState({ outgoing: [], incoming: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (nodeId) {
      fetchIdentityCard()
    }
  }, [nodeId])

  const fetchIdentityCard = async () => {
    setLoading(true)
    try {
      const [identityRes, neighborsRes] = await Promise.all([
        getIdentityCard(nodeId),
        getNeighbors(nodeId)
      ])

      if (identityRes.data.success) {
        setIdentity(identityRes.data.data)
      }
      if (neighborsRes.data.success) {
        setNeighbors({
          outgoing: neighborsRes.data.data.outgoing || [],
          incoming: neighborsRes.data.data.incoming || []
        })
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (!nodeId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white">
        <div className="text-center text-slate-400">
          <div className="text-4xl mb-4">🌿</div>
          <div className="text-lg font-medium">Welcome to Sage</div>
          <div className="text-sm mt-2">Select a node from the sidebar to view its Identity Card.</div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white">
        <div className="text-slate-400">Loading Identity Card...</div>
      </div>
    )
  }

  if (!identity) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white">
        <div className="text-red-400">Failed to load Identity Card.</div>
      </div>
    )
  }

  const { identity: idInfo, overview, context, knowledge, activity, ai, metrics } = identity

  return (
    <div className="flex-1 bg-white overflow-y-auto">
      {/* Header */}
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{idInfo.icon || '📄'}</span>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{idInfo.title}</h1>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-600">{idInfo.type_display}</span>
              <span className="font-mono text-xs">{idInfo.slug}</span>
              <span className="text-xs">{metrics.completeness}% complete</span>
            </div>
          </div>
        </div>

        {/* Metrics Bar */}
        <div className="flex gap-4 mt-4">
          <MetricBadge label="Completeness" value={`${metrics.completeness}%`} 
            color={metrics.completeness >= 80 ? 'green' : metrics.completeness >= 50 ? 'yellow' : 'red'} />
          <MetricBadge label="Importance" value={metrics.importance ? `${(metrics.importance * 100).toFixed(0)}%` : 'N/A'} color="blue" />
          <MetricBadge label="Confidence" value={metrics.confidence} color="purple" />
          <MetricBadge label="Connections" value={neighbors.outgoing.length + neighbors.incoming.length} color="slate" />
        </div>
      </div>

      {/* Content Sections */}
      <div className="p-6 space-y-8">
        {/* Overview */}
        <Section title="Overview" icon="📝">
          <div className="text-sm text-slate-700 leading-relaxed">
            {overview.summary || overview.description || 'No overview available.'}
          </div>
          {overview.description && overview.description !== overview.summary && (
            <div className="mt-3 text-sm text-slate-600 whitespace-pre-wrap">{overview.description}</div>
          )}
        </Section>

        {/* Current State */}
        <Section title="Current State" icon="📊">
          <div className="grid grid-cols-2 gap-4">
            <StateField label="Status" value={context.current_state} />
            <StateField label="Layer" value={context.layer} />
            <StateField label="Priority" value={context.priority} />
            <StateField label="Last Updated" value={metrics.last_updated ? new Date(metrics.last_updated).toLocaleDateString() : 'Never'} />
          </div>
        </Section>

        {/* Timeline Events */}
        {context.timeline_events.length > 0 && (
          <Section title="Timeline" icon="📅">
            <div className="space-y-2">
              {context.timeline_events.map((event, i) => (
                <div key={i} className="flex gap-3 items-start p-2 rounded-lg bg-slate-50">
                  <div className="text-xs font-mono text-slate-400 whitespace-nowrap">
                    {event.date ? new Date(event.date).toLocaleDateString() : 'Unknown'}
                  </div>
                  <div className="text-sm text-slate-700">{event.title}</div>
                  <div className={`text-xs px-1.5 py-0.5 rounded ml-auto ${
                    event.importance === 'high' ? 'bg-red-100 text-red-700' :
                    event.importance === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {event.importance}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Relationships */}
        <Section title="Relationships" icon="🔗">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-slate-600 mb-2">Outgoing ({neighbors.outgoing.length})</div>
              {neighbors.outgoing.map((rel, i) => (
                <div key={i} className="flex items-center gap-2 text-sm p-2 bg-slate-50 rounded mb-1">
                  <span className="text-xs text-slate-400">→</span>
                  <span className="font-medium">{rel.target.title}</span>
                  <span className="text-xs text-slate-500 ml-auto">{rel.relationship_display}</span>
                </div>
              ))}
              {neighbors.outgoing.length === 0 && (
                <div className="text-sm text-slate-400 italic">No outgoing relationships.</div>
              )}
            </div>
            <div>
              <div className="text-sm font-medium text-slate-600 mb-2">Incoming ({neighbors.incoming.length})</div>
              {neighbors.incoming.map((rel, i) => (
                <div key={i} className="flex items-center gap-2 text-sm p-2 bg-slate-50 rounded mb-1">
                  <span className="text-xs text-slate-400">←</span>
                  <span className="font-medium">{rel.source.title}</span>
                  <span className="text-xs text-slate-500 ml-auto">{rel.relationship_display}</span>
                </div>
              ))}
              {neighbors.incoming.length === 0 && (
                <div className="text-sm text-slate-400 italic">No incoming relationships.</div>
              )}
            </div>
          </div>
        </Section>

        {/* Knowledge */}
        <Section title="Knowledge" icon="🧠">
          <div className="space-y-3">
            {knowledge.evidence.length > 0 && (
              <div>
                <div className="text-sm font-medium text-slate-600 mb-1">Evidence ({knowledge.evidence.length})</div>
                {knowledge.evidence.map((e, i) => (
                  <div key={i} className="text-sm text-slate-700 p-2 bg-slate-50 rounded">{e.title || 'Untitled'}</div>
                ))}
              </div>
            )}
            {knowledge.evidence.length === 0 && (
              <div className="text-sm text-slate-400 italic">No evidence recorded yet.</div>
            )}
          </div>
        </Section>

        {/* Activity */}
        <Section title="Activity" icon="📈">
          <div className="space-y-3">
            {activity.recent_changes.length > 0 && (
              <div>
                <div className="text-sm font-medium text-slate-600 mb-1">Recent Changes</div>
                {activity.recent_changes.map((change, i) => (
                  <div key={i} className="flex gap-2 text-sm p-2 bg-slate-50 rounded">
                    <span className="text-xs text-slate-400">
                      {change.date ? new Date(change.date).toLocaleDateString() : 'Unknown'}
                    </span>
                    <span className="text-slate-700">{change.summary}</span>
                    <span className={`text-xs px-1.5 rounded ml-auto ${
                      change.type === 'created' ? 'bg-green-100 text-green-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {change.type}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {activity.recent_changes.length === 0 && (
              <div className="text-sm text-slate-400 italic">No recent changes.</div>
            )}
          </div>
        </Section>

        {/* AI Analysis */}
        <Section title="AI Analysis" icon="🤖">
          <div className="space-y-3">
            {ai.summary && (
              <div className="text-sm text-slate-700 bg-sage-50 p-3 rounded-lg">{ai.summary}</div>
            )}
            {ai.missing_information && (
              <div className="text-sm text-amber-600">
                <span className="font-medium">Missing: </span>{ai.missing_information}
              </div>
            )}
            {ai.suggestions.length > 0 && (
              <div>
                <div className="text-sm font-medium text-slate-600 mb-1">Suggestions</div>
                {ai.suggestions.map((s, i) => (
                  <div key={i} className="text-sm text-slate-700 p-2 bg-slate-50 rounded">{s}</div>
                ))}
              </div>
            )}
            {!ai.summary && !ai.missing_information && ai.suggestions.length === 0 && (
              <div className="text-sm text-slate-400 italic">AI analysis not yet generated. Populate this knowledge object to get insights.</div>
            )}
          </div>
        </Section>

        {/* Completeness Breakdown */}
        <Section title="Completeness" icon="✅">
          <div className="space-y-2">
            {Object.entries(metrics.completeness_breakdown || {}).map(([key, value]) => (
              <div key={key} className="flex items-center gap-3">
                <div className="w-4">{value ? '✓' : '○'}</div>
                <div className="flex-1 text-sm text-slate-700 capitalize">{key}</div>
                <div className={`text-xs px-2 py-0.5 rounded ${
                  value ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  {value ? 'Complete' : 'Missing'}
                </div>
              </div>
            ))}
            {Object.keys(metrics.completeness_breakdown || {}).length === 0 && (
              <div className="text-sm text-slate-400 italic">No completeness metrics yet.</div>
            )}
          </div>
        </Section>
      </div>
    </div>
  )
}

// Helper Components
function Section({ title, icon, children }) {
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
        <span>{icon}</span>
        <span className="font-semibold text-slate-700">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function MetricBadge({ label, value, color }) {
  const colors = {
    green: 'bg-green-50 text-green-700 border-green-200',
    yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    slate: 'bg-slate-50 text-slate-700 border-slate-200',
  }
  
  return (
    <div className={`px-3 py-2 rounded-lg border ${colors[color] || colors.slate}`}>
      <div className="text-xs font-medium opacity-70">{label}</div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  )
}

function StateField({ label, value }) {
  return (
    <div className="p-3 bg-slate-50 rounded-lg">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-sm font-medium text-slate-700">{value || '—'}</div>
    </div>
  )
}

export default IdentityCard
