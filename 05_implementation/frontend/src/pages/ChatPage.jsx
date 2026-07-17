import React, { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { getLifeDomains, createThought, sendMessage, sendLayerMessage, getLayerChatHistory, uploadDocument } from '../services/api'

const LAYER_TABS = [
  { id: 'general', label: 'General', color: 'bg-slate-100 text-slate-700', activeColor: 'bg-slate-600 text-white' },
  { id: 'life', label: 'Life', color: 'bg-emerald-100 text-emerald-700', activeColor: 'bg-emerald-600 text-white' },
  { id: 'project', label: 'Projects', color: 'bg-amber-100 text-amber-700', activeColor: 'bg-amber-600 text-white' },
  { id: 'knowledge', label: 'Knowledge', color: 'bg-indigo-100 text-indigo-700', activeColor: 'bg-indigo-600 text-white' },
  { id: 'system', label: 'System', color: 'bg-slate-100 text-slate-700', activeColor: 'bg-slate-600 text-white' },
]

const LAYER_DESCRIPTIONS = {
  general: 'Ask me anything about your projects, life, or ideas.',
  life: 'Talk about Self, Career, Finance, Health — your life domains.',
  project: 'Discuss Sage, Kaal, ReRoot, Navgunjara — your active projects.',
  knowledge: 'Share research, book insights, or learning notes.',
  system: 'Ask how Sage works, or suggest improvements.',
}

const WELCOME_MESSAGES = {
  general: "Hey Shubhi! I'm Sage — your Chief of Staff. I'm here to track your projects, organize your thoughts, and help you stay focused. What's on your mind today?",
  life: "Welcome to your Life layer, Shubhi. This is where we manage your personal world — health, career, finance, dreams. What area do you want to talk about?",
  project: "Hey Shubhi! Ready to dive into your projects? I've got context on Sage, Kaal, ReRoot, and Navgunjara. Which one are we working on today?",
  knowledge: "Welcome to the Knowledge layer, Shubhi. Dump your research, book notes, and learning here. I'll connect it to your projects when it matters. What did you discover today?",
  system: "Hey Shubhi — this is the System layer. Here you can ask how Sage works, suggest features, or just give me feedback on what I should improve.",
}

function ChatPage({ activeDomain, setActiveDomain }) {
  const { domainId } = useParams()
  const [domains, setDomains] = useState([])
  const [activeLayer, setActiveLayer] = useState('general')
  const [layerMessages, setLayerMessages] = useState({
    general: [], life: [], project: [], knowledge: [], system: []
  })
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [showDomainPicker, setShowDomainPicker] = useState(false)
  const [pendingFile, setPendingFile] = useState(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  const messages = layerMessages[activeLayer] || []
  const currentLayer = LAYER_TABS.find(t => t.id === activeLayer)

  useEffect(() => { fetchDomains(); fetchChatHistory() }, [])
  useEffect(() => { if (domainId) { const d = domains.find(d => d.id === domainId); if (d) setActiveDomain(d) } }, [domainId, domains])
  useEffect(() => { scrollToBottom() }, [messages])

  const fetchDomains = async () => {
    try { const r = await getLifeDomains(); setDomains(r.data) } catch (e) { console.error(e) }
  }

  const fetchChatHistory = async () => {
    try {
      for (const layer of LAYER_TABS.map(t => t.id)) {
        const r = await getLayerChatHistory(layer)
        setLayerMessages(prev => ({ ...prev, [layer]: r.data.map(m => ({ id: m.id, role: m.role, content: m.content, timestamp: m.created_at })) }))
      }
    } catch (e) { console.error('Error fetching history:', e) }
  }

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    const userMsg = { id: Date.now(), role: 'user', content: inputMessage, timestamp: new Date().toISOString() }
    setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], userMsg] }))
    setInputMessage('')
    setIsLoading(true)

    try {
      const r = await sendLayerMessage(activeLayer, inputMessage)
      const sageMsg = { id: Date.now() + 1, role: 'sage', content: r.data.response, timestamp: new Date().toISOString() }
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], sageMsg] }))
    } catch (e) {
      console.error(e)
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], { id: Date.now() + 1, role: 'sage', content: 'Sorry, there was an error.', timestamp: new Date().toISOString() }] }))
    } finally { setIsLoading(false) }
  }

  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return
    if (activeDomain) { await performUpload(file, activeDomain) }
    else { setPendingFile(file); setShowDomainPicker(true) }
    event.target.value = ''
  }

  const performUpload = async (file, domain) => {
    setIsUploading(true)
    try {
      const r = await uploadDocument(domain ? domain.id : null, file)
      const msg = `Uploaded "${r.data.filename}" to ${domain ? domain.name : 'general memory'}.\n\n${r.data.summary || 'No summary'}`
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], { id: Date.now(), role: 'sage', content: msg, timestamp: new Date().toISOString() }] }))
    } catch (e) {
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], { id: Date.now(), role: 'sage', content: 'Upload failed.', timestamp: new Date().toISOString() }] }))
    } finally { setIsUploading(false) }
  }

  const handleKeyPress = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage() } }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="px-4 pt-3 pb-1 border-b border-sage-200 bg-white">
        <div className="flex items-center gap-1">
          {LAYER_TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveLayer(tab.id)}
              className={`px-3 py-1.5 text-sm font-medium rounded-t-lg border-b-2 transition-all ${activeLayer === tab.id ? `${tab.activeColor} border-current` : `${tab.color} border-transparent hover:opacity-80`}`}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="px-6 py-3 border-b border-sage-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-sage-800">{currentLayer?.label} Chat</h1>
            <p className="text-sm text-sage-500">{LAYER_DESCRIPTIONS[activeLayer]}</p>
          </div>
          <button onClick={() => fileInputRef.current?.click()} disabled={isUploading}
            className="px-3 py-2 text-sm bg-sage-100 text-sage-700 rounded-lg hover:bg-sage-200 disabled:opacity-50 transition-colors">
            {isUploading ? 'Uploading...' : 'Upload'}
          </button>
          <input ref={fileInputRef} type="file" onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.md,.docx" />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex justify-start">
            <div className="max-w-3xl px-4 py-3 rounded-2xl bg-white border border-sage-200 text-sage-800">
              <div className="text-sm whitespace-pre-wrap">{WELCOME_MESSAGES[activeLayer]}</div>
              <div className="text-xs mt-1 text-sage-400">{new Date().toLocaleTimeString()}</div>
            </div>
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-3xl px-4 py-3 rounded-2xl ${msg.role === 'user' ? 'bg-sage-600 text-white' : 'bg-white border border-sage-200 text-sage-800'}`}>
              <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
              <div className={`text-xs mt-1 ${msg.role === 'user' ? 'text-sage-200' : 'text-sage-400'}`}>{new Date(msg.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-sage-200 px-4 py-3 rounded-2xl">
              <div className="flex items-center gap-2 text-sage-500">
                <div className="w-2 h-2 bg-sage-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-sage-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                <div className="w-2 h-2 bg-sage-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-sage-200 bg-white">
        <div className="flex items-end gap-2">
          <textarea value={inputMessage} onChange={e => setInputMessage(e.target.value)} onKeyPress={handleKeyPress}
            placeholder={`Message ${currentLayer?.label}...`} disabled={isLoading}
            className="flex-1 px-4 py-3 border border-sage-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-sage-500 disabled:opacity-50"
            rows={1} style={{ minHeight: '44px', maxHeight: '120px' }} />
          <button onClick={handleSendMessage} disabled={!inputMessage.trim() || isLoading}
            className="px-4 py-3 bg-sage-600 text-white rounded-xl hover:bg-sage-700 disabled:opacity-50 transition-colors">Send</button>
        </div>
      </div>
    </div>
  )
}

export default ChatPage
