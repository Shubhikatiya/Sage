import React, { useState } from 'react'
import KnowledgeExplorer from './components/KnowledgeExplorer'
import IdentityCard from './components/IdentityCard'
import WorkspaceSession from './components/WorkspaceSession'
import AssetUploader from './components/AssetUploader'
import BringMeBack from './components/BringMeBack'
import ChatPage_v4 from './pages/ChatPage_v4'
import DashboardPage_v4 from './pages/DashboardPage_v4'
import SystemStatus from './components/SystemStatus'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '🎯' },
  { id: 'knowledge', label: 'Knowledge', icon: '🕸️' },
  { id: 'chat', label: 'Chat', icon: '💬' },
]

function App_v4() {
  const [activeView, setActiveView] = useState('dashboard')
  const [activeNodeId, setActiveNodeId] = useState(null)
  const [rightPanelTab, setRightPanelTab] = useState('workspace')

  const navigateToChat = () => setActiveView('chat')
  const navigateToGraph = (nodeId = null) => {
    setActiveView('knowledge')
    if (nodeId) setActiveNodeId(nodeId)
  }

  return (
    <div className="app-v4">
      {/* Top Navigation */}
      <nav className="top-nav">
        <div className="nav-brand">
          <span className="nav-icon">🧠</span>
          <span className="nav-title">Sage v4</span>
        </div>
        
        <div className="nav-items">
          {NAV_ITEMS.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activeView === item.id ? 'active' : ''}`}
              onClick={() => setActiveView(item.id)}
            >
              <span className="nav-item-icon">{item.icon}</span>
              <span className="nav-item-label">{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* DASHBOARD VIEW */}
        {activeView === 'dashboard' && (
          <DashboardPage_v4 
            onNavigateToChat={navigateToChat}
            onNavigateToGraph={navigateToGraph}
          />
        )}

        {/* KNOWLEDGE GRAPH VIEW */}
        {activeView === 'knowledge' && (
          <div className="knowledge-layout">
            {/* Left Sidebar */}
            <div className="sidebar-left">
              <KnowledgeExplorer
                activeNodeId={activeNodeId}
                setActiveNodeId={setActiveNodeId}
              />
            </div>

            {/* Center */}
            <div className="center-panel">
              <IdentityCard nodeId={activeNodeId} />
            </div>

            {/* Right Panel */}
            <div className="sidebar-right">
              <div className="tabs">
                <button 
                  className={`tab ${rightPanelTab === 'workspace' ? 'active' : ''}`}
                  onClick={() => setRightPanelTab('workspace')}
                >
                  🎯
                </button>
                <button 
                  className={`tab ${rightPanelTab === 'assets' ? 'active' : ''}`}
                  onClick={() => setRightPanelTab('assets')}
                >
                  📁
                </button>
                <button 
                  className={`tab ${rightPanelTab === 'bring-me-back' ? 'active' : ''}`}
                  onClick={() => setRightPanelTab('bring-me-back')}
                >
                  🧠
                </button>
              </div>

              <div className="tab-content">
                {rightPanelTab === 'workspace' && (
                  <WorkspaceSession activeNodeId={activeNodeId} />
                )}
                {rightPanelTab === 'assets' && (
                  <AssetUploader onUploadComplete={(data) => console.log('Upload:', data)} />
                )}
                {rightPanelTab === 'bring-me-back' && (
                  <BringMeBack sinceDays={7} />
                )}
              </div>
            </div>
          </div>
        )}

        {/* CHAT VIEW */}
        {activeView === 'chat' && (
          <ChatPage_v4 />
        )}
      </main>

      <style jsx>{`
        .app-v4 {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #f1f5f9;
          overflow: hidden;
        }
        
        .top-nav {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 1.5rem;
          height: 56px;
          background: white;
          border-bottom: 1px solid #e2e8f0;
          flex-shrink: 0;
        }
        
        .nav-brand {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .nav-icon {
          font-size: 1.25rem;
        }
        
        .nav-title {
          font-size: 1.1rem;
          font-weight: 700;
          color: #1e293b;
        }
        
        .nav-items {
          display: flex;
          gap: 0.25rem;
        }
        
        .nav-item {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.5rem 1rem;
          border: none;
          background: transparent;
          color: #64748b;
          font-size: 0.9rem;
          font-weight: 500;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s;
          font-family: inherit;
        }
        
        .nav-item:hover {
          background: #f1f5f9;
          color: #475569;
        }
        
        .nav-item.active {
          background: #eff6ff;
          color: #3b82f6;
        }
        
        .nav-item-icon {
          font-size: 1rem;
        }
        
        .main-content {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .knowledge-layout {
          display: flex;
          height: 100%;
          overflow: hidden;
        }
        
        .sidebar-left {
          width: 280px;
          min-width: 280px;
          background: white;
          border-right: 1px solid #e2e8f0;
          overflow-y: auto;
        }
        
        .center-panel {
          flex: 1;
          overflow-y: auto;
          background: #f8fafc;
        }
        
        .sidebar-right {
          width: 380px;
          min-width: 380px;
          background: white;
          border-left: 1px solid #e2e8f0;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        
        .tabs {
          display: flex;
          border-bottom: 1px solid #e2e8f0;
          background: #f8fafc;
        }
        
        .tab {
          flex: 1;
          padding: 0.75rem;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 1.1rem;
          transition: background 0.15s;
          border-bottom: 2px solid transparent;
        }
        
        .tab:hover {
          background: #f1f5f9;
        }
        
        .tab.active {
          border-bottom-color: #3b82f6;
          background: white;
        }
        
        .tab-content {
          flex: 1;
          overflow-y: auto;
        }
        
        @media (max-width: 1200px) {
          .sidebar-right {
            width: 320px;
            min-width: 320px;
          }
        }
        
        @media (max-width: 900px) {
          .sidebar-right {
            display: none;
          }
          
          .sidebar-left {
            width: 240px;
            min-width: 240px;
          }
        }
        
        @media (max-width: 640px) {
          .sidebar-left {
            display: none;
          }
          
          .nav-item-label {
            display: none;
          }
        }
      `}</style>
      <SystemStatus />
    </div>
  )
}

export default App_v4
