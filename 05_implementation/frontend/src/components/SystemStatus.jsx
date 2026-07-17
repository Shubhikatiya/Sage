import { useState, useEffect } from 'react'
import { getLLMStatus, getDegradationFlags } from '../services/api_v4'

export default function SystemStatus() {
  const [llmStatus, setLlmStatus] = useState(null)
  const [flags, setFlags] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    async function fetchStatus() {
      try {
        const [llm, deg] = await Promise.all([
          getLLMStatus(),
          getDegradationFlags()
        ])
        if (llm.data?.success) setLlmStatus(llm.data.data)
        if (deg.data?.success) setFlags(deg.data.data)
      } catch (e) {
        console.error('System status error:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  if (loading) return null

  const providers = llmStatus?.available_providers || []
  const isDegraded = providers.length === 0 || !flags?.llm_available

  return (
    <div className={`fixed bottom-4 right-4 z-50 rounded-lg shadow-lg border ${isDegraded ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium"
      >
        <span className={`w-2 h-2 rounded-full ${isDegraded ? 'bg-red-500' : 'bg-green-500'}`} />
        <span className={isDegraded ? 'text-red-700' : 'text-gray-700'}>
          {isDegraded ? 'Degraded' : 'Healthy'}
        </span>
        <span className="text-gray-400 text-xs">{providers.length} provider{providers.length !== 1 ? 's' : ''}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-gray-100 min-w-[280px]">
          <div className="space-y-2 mt-2">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">LLM Providers</div>
            {providers.map(p => (
              <div key={p} className="flex items-center justify-between text-sm">
                <span className="capitalize text-gray-700">{p}</span>
                <span className="w-2 h-2 rounded-full bg-green-400" />
              </div>
            ))}
            {providers.length === 0 && (
              <div className="text-sm text-red-600">No LLM providers available</div>
            )}

            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-3">Subsystems</div>
            {flags && Object.entries(flags).map(([name, ok]) => (
              <div key={name} className="flex items-center justify-between text-sm">
                <span className="text-gray-700 capitalize">{name.replace('_', ' ')}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {ok ? 'Up' : 'Down'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
