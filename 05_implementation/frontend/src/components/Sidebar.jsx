import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getLifeDomains, createLifeDomain, deleteLifeDomain, updateLifeDomain, createSubsection, getDomainDocuments } from '../services/api'

const LAYER_CONFIG = {
  life: {
    label: 'Life',
    icon: '👤',
    color: 'emerald',
    description: 'Who you are'
  },
  project: {
    label: 'Projects',
    icon: '🚀',
    color: 'amber',
    description: 'What you are building'
  },
  knowledge: {
    label: 'Knowledge',
    icon: '🧠',
    color: 'indigo',
    description: 'What you are learning'
  },
  system: {
    label: 'System',
    icon: '⚙️',
    color: 'slate',
    description: 'How Sage works'
  }
}

function Sidebar({ activeDomain, setActiveDomain, selectedDocument, setSelectedDocument }) {
  const [domains, setDomains] = useState([])
  const [domainDocs, setDomainDocs] = useState({})  // domainId -> [documents]
  const [expandedDomains, setExpandedDomains] = useState({})  // domainId -> bool
  const [newDomainName, setNewDomainName] = useState('')
  const [newDomainLayer, setNewDomainLayer] = useState('life')
  const [isCreating, setIsCreating] = useState(false)
  const [editingDomain, setEditingDomain] = useState(null)
  const [editName, setEditName] = useState('')
  const [addingSubsection, setAddingSubsection] = useState(null)
  const [subsectionName, setSubsectionName] = useState('')
  const [expandedLayers, setExpandedLayers] = useState({
    life: true,
    project: true,
    knowledge: true,
    system: false
  })
  const location = useLocation()

  useEffect(() => {
    fetchDomains()
  }, [])

  const fetchDomains = async () => {
    try {
      const [lifeRes, projectRes, knowledgeRes, systemRes] = await Promise.all([
        getLifeDomains('life'),
        getLifeDomains('project'),
        getLifeDomains('knowledge'),
        getLifeDomains('system'),
      ])
      const all = [
        ...lifeRes.data,
        ...projectRes.data,
        ...knowledgeRes.data,
        ...systemRes.data,
      ]
      setDomains(all)
      // Fetch documents for each domain
      for (const d of all) {
        try {
          const docRes = await getDomainDocuments(d.id)
          setDomainDocs(prev => ({ ...prev, [d.id]: docRes.data }))
        } catch (e) {}
      }
    } catch (error) {
      console.error('Error fetching layers:', error)
    }
  }

  const toggleDomain = (domainId) => {
    setExpandedDomains(prev => ({ ...prev, [domainId]: !prev[domainId] }))
  }

  const handleCreateDomain = async () => {
    if (!newDomainName.trim()) return
    try {
      const response = await createLifeDomain({
        name: newDomainName,
        description: '',
        layer: newDomainLayer
      })
      setDomains([...domains, response.data])
      setNewDomainName('')
      setIsCreating(false)
    } catch (error) {
      console.error('Error creating domain:', error)
    }
  }

  const handleDelete = async (id, e) => {
    e?.stopPropagation()
    if (!confirm('Delete this item? This cannot be undone.')) return
    try {
      await deleteLifeDomain(id)
      setDomains(domains.filter(d => d.id !== id))
      if (activeDomain?.id === id) setActiveDomain(null)
    } catch (error) {
      console.error('Error deleting:', error)
    }
  }

  const handleRename = async (domain) => {
    if (!editName.trim()) {
      setEditingDomain(null)
      return
    }
    try {
      const response = await updateLifeDomain(domain.id, { name: editName })
      setDomains(domains.map(d => d.id === domain.id ? response.data : d))
      if (activeDomain?.id === domain.id) setActiveDomain(response.data)
      setEditingDomain(null)
    } catch (error) {
      console.error('Error renaming:', error)
    }
  }

  const handleCreateSubsection = async (parentId) => {
    if (!subsectionName.trim()) {
      setAddingSubsection(null)
      return
    }
    try {
      const response = await createSubsection(parentId, subsectionName, '')
      setDomains([...domains, response.data])
      setSubsectionName('')
      setAddingSubsection(null)
    } catch (error) {
      console.error('Error creating subsection:', error)
    }
  }

  const toggleLayer = (layer) => {
    setExpandedLayers({ ...expandedLayers, [layer]: !expandedLayers[layer] })
  }

  // Organize domains by layer and parent
  const domainsByLayer = {}
  Object.keys(LAYER_CONFIG).forEach(layer => {
    domainsByLayer[layer] = {
      topLevel: domains.filter(d => d.layer === layer && !d.parent_id),
      children: domains.filter(d => d.layer === layer && d.parent_id)
    }
  })

  const getChildren = (parentId) => domains.filter(d => d.parent_id === parentId)

  const renderDomain = (domain, layerConfig, isChild = false) => {
    const children = getChildren(domain.id)
    const docs = domainDocs[domain.id] || []
    const isActive = activeDomain?.id === domain.id
    const isEditing = editingDomain === domain.id
    const isAddingSub = addingSubsection === domain.id
    const isExpanded = expandedDomains[domain.id]
    const colorClass = layerConfig.color

    return (
      <div key={domain.id}>
        <div className="group relative">
          {isEditing ? (
            <div className="flex gap-1 mb-1">
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleRename(domain)}
                onBlur={() => handleRename(domain)}
                className={`w-full px-2 py-1 text-sm border border-${colorClass}-300 rounded focus:outline-none focus:ring-1 focus:ring-${colorClass}-500`}
                autoFocus
              />
            </div>
          ) : (
            <div
              onClick={() => {
                setActiveDomain(domain)
                toggleDomain(domain.id)
              }}
              className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
                isActive 
                  ? `bg-${colorClass}-100 text-${colorClass}-800` 
                  : `text-${colorClass}-600 hover:bg-${colorClass}-50`
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`text-xs ${isExpanded ? 'rotate-90' : ''} transition-transform`}>▶</span>
                <span className={`${isChild ? 'text-xs' : 'text-sm'}`}>{domain.name}</span>
                {docs.length > 0 && <span className="text-[10px] text-slate-400">({docs.length})</span>}
              </div>
              <div className="hidden group-hover:flex gap-1">
                {!isChild && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setAddingSubsection(domain.id); setSubsectionName('') }}
                    className={`text-xs text-${colorClass}-500 hover:text-${colorClass}-700 px-1`}
                    title="Add subsection"
                  >
                    +
                  </button>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); setEditingDomain(domain.id); setEditName(domain.name) }}
                  className={`text-xs text-${colorClass}-500 hover:text-${colorClass}-700 px-1`}
                  title="Rename"
                >
                  ✎
                </button>
                <button
                  onClick={(e) => handleDelete(domain.id, e)}
                  className="text-xs text-red-400 hover:text-red-600 px-1"
                  title="Delete"
                >
                  ×
                </button>
              </div>
            </div>
          )}
        </div>

        {isAddingSub && (
          <div className={`ml-3 pl-2 border-l border-${colorClass}-200 mb-2`}>
            <input
              type="text"
              value={subsectionName}
              onChange={(e) => setSubsectionName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleCreateSubsection(domain.id)}
              placeholder="Subsection name..."
              className={`w-full px-2 py-1 text-xs border border-${colorClass}-300 rounded focus:outline-none focus:ring-1 focus:ring-${colorClass}-500`}
              autoFocus
            />
            <div className="flex gap-1 mt-1">
              <button onClick={() => handleCreateSubsection(domain.id)} className={`text-xs px-2 py-0.5 bg-${colorClass}-600 text-white rounded`}>Add</button>
              <button onClick={() => setAddingSubsection(null)} className={`text-xs px-2 py-0.5 border border-${colorClass}-300 rounded`}>Cancel</button>
            </div>
          </div>
        )}

        {/* Documents under this domain */}
        {isExpanded && docs.length > 0 && (
          <div className="ml-4 pl-2 border-l border-slate-200 space-y-0.5 mb-1">
            {docs.map(doc => (
              <div 
                key={doc.id}
                onClick={(e) => {
                  e.stopPropagation()
                  setSelectedDocument(doc)
                }}
                className={`flex items-center gap-1.5 px-2 py-1 text-xs rounded cursor-pointer transition-colors ${
                  selectedDocument?.id === doc.id 
                    ? 'bg-slate-200 text-slate-800' 
                    : 'text-slate-500 hover:bg-slate-50'
                }`}
                title={doc.content ? (doc.content.length <= 100 ? doc.content : doc.content.slice(0, doc.content.lastIndexOf(' ', 100)) + '...') : 'Empty document'}
              >
                <span>📄</span>
                <span className="truncate">
                  {doc.title || doc.document_type || 'Document'} {doc.version > 1 && `(v${doc.version})`}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Subsections */}
        {children.length > 0 && (
          <div className={`ml-3 pl-2 border-l border-${colorClass}-200 space-y-0.5`}>
            {children.map(child => renderDomain(child, layerConfig, true))}
          </div>
        )}
      </div>
    )
  }

  const renderLayerSection = (layer) => {
    const config = LAYER_CONFIG[layer]
    const data = domainsByLayer[layer]
    const isExpanded = expandedLayers[layer]
    const count = data.topLevel.length

    return (
      <div key={layer} className="mb-4">
        <button
          onClick={() => toggleLayer(layer)}
          className={`flex items-center justify-between w-full px-2 py-2 rounded-lg text-sm font-medium transition-colors bg-${config.color}-50 hover:bg-${config.color}-100 text-${config.color}-700`}
        >
          <div className="flex items-center gap-2">
            <span>{config.icon}</span>
            <span>{config.label}</span>
            <span className={`text-xs text-${config.color}-400`}>({count})</span>
          </div>
          <span className={`text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
        </button>

        {isExpanded && (
          <div className="mt-1 space-y-0.5">
            {data.topLevel.length === 0 ? (
              <div className={`px-3 py-2 text-xs text-${config.color}-400 italic`}>
                No {config.label.toLowerCase()} yet
              </div>
            ) : (
              data.topLevel.map(domain => renderDomain(domain, config))
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="w-80 bg-white border-r border-slate-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <Link to="/" className="flex items-center gap-2 text-slate-800 hover:text-slate-600">
          <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">S</div>
          <div>
            <span className="text-lg font-semibold">Sage</span>
            <div className="text-xs text-slate-400">AI Chief of Staff</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        {/* Quick links */}
        <div className="mb-4 space-y-1">
          <Link 
            to="/" 
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm ${location.pathname === '/' ? 'bg-slate-100 text-slate-800' : 'text-slate-600 hover:bg-slate-50'}`}
          >
            <span>📊</span> Dashboard
          </Link>
          <Link 
            to="/chat" 
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm ${location.pathname.startsWith('/chat') ? 'bg-slate-100 text-slate-800' : 'text-slate-600 hover:bg-slate-50'}`}
          >
            <span>💬</span> Chat
          </Link>
        </div>

        {/* Create new */}
        <div className="mb-4">
          {!isCreating ? (
            <button
              onClick={() => setIsCreating(true)}
              className="w-full flex items-center justify-center gap-1 px-3 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
            >
              <span>+</span> Add Item
            </button>
          ) : (
            <div className="space-y-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <select
                value={newDomainLayer}
                onChange={(e) => setNewDomainLayer(e.target.value)}
                className="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option value="life">Life Domain</option>
                <option value="project">Project</option>
                <option value="knowledge">Knowledge</option>
                <option value="system">System</option>
              </select>
              <input
                type="text"
                value={newDomainName}
                onChange={(e) => setNewDomainName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateDomain()}
                placeholder="Name..."
                className="w-full px-2 py-1 text-sm border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-emerald-500"
                autoFocus
              />
              <div className="flex gap-2">
                <button onClick={handleCreateDomain} className="flex-1 text-xs px-2 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700">Create</button>
                <button onClick={() => setIsCreating(false)} className="text-xs px-2 py-1 border border-slate-300 rounded hover:bg-slate-100">Cancel</button>
              </div>
            </div>
          )}
        </div>

        {/* Layer sections */}
        {Object.keys(LAYER_CONFIG).map(layer => renderLayerSection(layer))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200">
        <div className="text-xs text-slate-400 text-center">
          Sage v0.2.0
        </div>
      </div>
    </div>
  )
}

export default Sidebar
