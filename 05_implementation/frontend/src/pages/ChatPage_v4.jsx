import React, { useState, useEffect, useRef } from 'react'
import { getSidebar, bringMeBack, sendChatMessage, clearChatHistory } from '../services/api_v4'

const LAYER_TABS = [
  { id: 'general', label: 'General', color: 'bg-slate-100 text-slate-700', activeColor: 'bg-slate-600 text-white' },
  { id: 'life', label: 'Life', color: 'bg-emerald-100 text-emerald-700', activeColor: 'bg-emerald-600 text-white' },
  { id: 'project', label: 'Projects', color: 'bg-amber-100 text-amber-700', activeColor: 'bg-amber-600 text-white' },
  { id: 'knowledge', label: 'Knowledge', color: 'bg-indigo-100 text-indigo-700', activeColor: 'bg-indigo-600 text-white' },
  { id: 'system', label: 'System', color: 'bg-slate-100 text-slate-700', activeColor: 'bg-slate-600 text-white' },
]

const LAYER_DESCRIPTIONS = {
  general: 'Ask me anything about your projects, life, or ideas.',
  life: 'Talk about Self, Career, Finance, Health \u2014 your life domains.',
  project: 'Discuss Sage, Kaal, ReRoot, Navgunjara \u2014 your active projects.',
  knowledge: 'Share research, book insights, or learning notes.',
  system: 'Ask how Sage works, or suggest improvements.',
}

const WELCOME_MESSAGES = {
  general: "Hey Shubhi! I'm Sage \u2014 your Chief of Staff. I'm here to track your projects, organize your thoughts, and help you stay focused. What's on your mind today?",
  life: "Welcome to your Life layer, Shubhi. This is where we manage your personal world \u2014 health, career, finance, dreams. What area do you want to talk about?",
  project: "Hey Shubhi! Ready to dive into your projects? I've got context on Sage, Kaal, ReRoot, and Navgunjara. Which one are we working on today?",
  knowledge: "Welcome to the Knowledge layer, Shubhi. Dump your research, book notes, and learning here. I'll connect it to your projects when it matters. What did you discover today?",
  system: "Hey Shubhi \u2014 this is the System layer. Here you can ask how Sage works, suggest features, or just give me feedback on what I should improve.",
}

function ChatPage_v4() {
  const [activeLayer, setActiveLayer] = useState('general')
  const [layerMessages, setLayerMessages] = useState({
    general: [], life: [], project: [], knowledge: [], system: []
  })
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const messages = layerMessages[activeLayer] || []
  const currentLayer = LAYER_TABS.find(t => t.id === activeLayer)

  useEffect(() => { scrollToBottom() }, [messages])

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    const userMsg = { id: Date.now(), role: 'user', content: inputMessage, timestamp: new Date().toISOString() }
    setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], userMsg] }))
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await sendChatMessage(activeLayer, inputMessage)
      const data = response.data.data
      
      const sageMsg = { 
        id: Date.now() + 1, 
        role: 'assistant', 
        content: data.message, 
        timestamp: data.timestamp || new Date().toISOString()
      }
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], sageMsg] }))
    } catch (e) {
      console.error(e)
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [...prev[activeLayer], { id: Date.now() + 1, role: 'assistant', content: 'Sorry, there was an error processing your request.', timestamp: new Date().toISOString() }] }))
    } finally { setIsLoading(false) }
  }

  const handleClearChat = async () => {
    if (!confirm('Clear chat history for this layer?')) return
    try {
      await clearChatHistory(activeLayer)
      setLayerMessages(prev => ({ ...prev, [activeLayer]: [] }))
    } catch (e) {
      console.error('Failed to clear chat:', e)
    }
  }

  const handleKeyPress = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage() } }

  return (
    <div className="chat-page-v4">
      {/* Tabs */}
      <div className="tabs-header">
        <div className="tabs-row">
          {LAYER_TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveLayer(tab.id)}
              className={`layer-tab ${activeLayer === tab.id ? 'active' : ''}`}
              style={{
                backgroundColor: activeLayer === tab.id ? '' : undefined,
                color: activeLayer === tab.id ? '' : undefined
              }}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="chat-header">
        <div className="header-info">
          <h1>{currentLayer?.label} Chat</h1>
          <p>{LAYER_DESCRIPTIONS[activeLayer]}</p>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-area">
        {messages.length === 0 && (
          <div className="message-row sage">
            <div className="message-bubble sage">
              <div className="message-content">{WELCOME_MESSAGES[activeLayer]}</div>
              <div className="message-time">{new Date().toLocaleTimeString()}</div>
            </div>
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={`message-row ${msg.role}`}>
            <div className={`message-bubble ${msg.role}`}>
              <div className="message-content" dangerouslySetInnerHTML={{ 
                __html: msg.content.replace(/\n/g, '<br/>').replace(/## (.*)/, '<h3>$1</h3>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/- (.*)/g, '<li>$1</li>') 
              }} />
              <div className="message-time">{new Date(msg.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-row sage">
            <div className="message-bubble sage loading">
              <div className="loading-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <textarea 
          value={inputMessage} 
          onChange={e => setInputMessage(e.target.value)} 
          onKeyPress={handleKeyPress}
          placeholder={`Message ${currentLayer?.label}...`} 
          disabled={isLoading}
          rows={1}
        />
        <button onClick={handleSendMessage} disabled={!inputMessage.trim() || isLoading}>
          Send
        </button>
      </div>

      <style jsx>{`
        .chat-page-v4 {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #f8fafc;
        }
        
        .tabs-header {
          padding: 0.75rem 1rem 0;
          background: white;
          border-bottom: 1px solid #e2e8f0;
        }
        
        .tabs-row {
          display: flex;
          gap: 0.25rem;
        }
        
        .layer-tab {
          padding: 0.5rem 1rem;
          border: none;
          background: #f1f5f9;
          color: #64748b;
          border-radius: 8px 8px 0 0;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          transition: all 0.15s;
        }
        
        .layer-tab:hover {
          background: #e2e8f0;
        }
        
        .layer-tab.active {
          background: #3b82f6;
          color: white;
        }
        
        .layer-tab.active[data-tab="life"] { background: #059669; }
        .layer-tab.active[data-tab="project"] { background: #d97706; }
        .layer-tab.active[data-tab="knowledge"] { background: #4f46e5; }
        .layer-tab.active[data-tab="system"] { background: #475569; }
        
        .chat-header {
          padding: 0.75rem 1rem;
          background: white;
          border-bottom: 1px solid #e2e8f0;
        }
        
        .header-info h1 {
          margin: 0;
          font-size: 1rem;
          color: #1e293b;
        }
        
        .header-info p {
          margin: 0.25rem 0 0;
          font-size: 0.8rem;
          color: #64748b;
        }
        
        .messages-area {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        
        .message-row {
          display: flex;
        }
        
        .message-row.user {
          justify-content: flex-end;
        }
        
        .message-row.sage {
          justify-content: flex-start;
        }
        
        .message-bubble {
          max-width: 80%;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          font-size: 0.9rem;
          line-height: 1.5;
        }
        
        .message-bubble.user {
          background: #3b82f6;
          color: white;
          border-bottom-right-radius: 4px;
        }
        
        .message-bubble.sage {
          background: white;
          border: 1px solid #e2e8f0;
          color: #1e293b;
          border-bottom-left-radius: 4px;
        }
        
        .message-bubble.sage :global(h3) {
          margin: 0 0 0.5rem;
          font-size: 1rem;
          color: #1e293b;
        }
        
        .message-bubble.sage :global(strong) {
          color: #1e293b;
        }
        
        .message-bubble.sage :global(li) {
          margin: 0.25rem 0;
          color: #475569;
        }
        
        .message-time {
          font-size: 0.7rem;
          margin-top: 0.25rem;
          opacity: 0.7;
        }
        
        .message-bubble.sage .message-time {
          color: #94a3b8;
        }
        
        .loading-dots {
          display: flex;
          gap: 0.3rem;
          padding: 0.25rem 0;
        }
        
        .loading-dots span {
          width: 8px;
          height: 8px;
          background: #94a3b8;
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out both;
        }
        
        .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
        .loading-dots span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
        
        .input-area {
          display: flex;
          gap: 0.5rem;
          padding: 1rem;
          background: white;
          border-top: 1px solid #e2e8f0;
        }
        
        .input-area textarea {
          flex: 1;
          padding: 0.75rem 1rem;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          resize: none;
          font-size: 0.9rem;
          font-family: inherit;
          min-height: 44px;
          max-height: 120px;
          outline: none;
        }
        
        .input-area textarea:focus {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .input-area button {
          padding: 0.75rem 1.5rem;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s;
        }
        
        .input-area button:hover:not(:disabled) {
          background: #2563eb;
        }
        
        .input-area button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  )
}

export default ChatPage_v4
