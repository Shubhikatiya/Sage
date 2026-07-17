import React, { useState, useEffect } from 'react'
import { getSidebar, searchKnowledge } from '../services/api_v4'

function KnowledgeExplorer({ activeNodeId, setActiveNodeId }) {
  const [sidebar, setSidebar] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSidebar()
  }, [])

  const fetchSidebar = async () => {
    try {
      const r = await getSidebar()
      if (r.data.success) {
        setSidebar(r.data.data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    try {
      const r = await searchKnowledge({ q: searchQuery })
      if (r.data.success) {
        setSearchResults(r.data.data.items || [])
      }
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return (
    <div className="w-72 bg-slate-50 border-r border-slate-200 p-4 flex items-center justify-center">
      <div className="text-slate-400 text-sm">Loading Knowledge Explorer...</div>
    </div>
  )

  return (
    <div className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-lg">🌿</span>
          <h1 className="font-semibold text-slate-800">Sage</h1>
        </div>
        {sidebar && (
          <div className="text-xs text-slate-500">
            {sidebar.workspace.name}
          </div>
        )}
      </div>

      {/* Search */}
      <div className="p-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search knowledge..."
            className="flex-1 px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-500"
          />
          <button
            onClick={handleSearch}
            className="px-3 py-1.5 text-sm bg-slate-800 text-white rounded-lg hover:bg-slate-700"
          >
            🔍
          </button>
        </div>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="px-3 pb-2">
          <div className="text-xs font-medium text-slate-500 mb-2">Search Results ({searchResults.length})</div>
          {searchResults.map((item) => (
            <div
              key={item.id}
              onClick={() => { setActiveNodeId(item.id); setSearchResults([]); setSearchQuery('') }}
              className={`px-3 py-2 rounded-lg cursor-pointer text-sm mb-1 transition-colors ${
                activeNodeId === item.id
                  ? 'bg-sage-100 text-sage-800'
                  : 'hover:bg-slate-100 text-slate-700'
              }`}
            >
              <div className="font-medium truncate">{item.title}</div>
              <div className="text-xs text-slate-400">{item.type_display} | {item.completeness_percent}% complete</div>
            </div>
          ))}
        </div>
      )}

      {/* Navigation Sections */}
      <div className="flex-1 px-3 pb-4">
        {sidebar && sidebar.sections.map((section) => (
          <div key={section.id} className="mb-4">
            <div className="flex items-center gap-2 mb-2 px-1">
              <span className="text-sm">{section.icon}</span>
              <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">{section.title}</span>
              <span className="text-xs text-slate-400 ml-auto">{section.items.length}</span>
            </div>

            {section.items.map((item) => (
              <div
                key={item.id}
                onClick={() => setActiveNodeId(item.id)}
                className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                  activeNodeId === item.id
                    ? 'bg-sage-100 text-sage-800'
                    : 'hover:bg-slate-100 text-slate-700'
                }`}
              >
                <div className="flex-1 truncate font-medium">{item.title}</div>
                {item.completeness !== undefined && (
                  <div className={`text-xs px-1.5 py-0.5 rounded ${
                    item.completeness >= 80 ? 'bg-green-100 text-green-700' :
                    item.completeness >= 50 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {item.completeness}%
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-slate-200 bg-slate-100">
        <div className="flex justify-between text-xs text-slate-500">
          <span>8 nodes</span>
          <span>7 relationships</span>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeExplorer
