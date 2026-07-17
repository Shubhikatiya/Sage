import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import DocumentViewer from './components/DocumentViewer'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'

function App() {
  const [activeDomain, setActiveDomain] = useState(null)
  const [selectedDocument, setSelectedDocument] = useState(null)

  return (
    <div className="flex h-screen bg-sage-50">
      <Sidebar 
        activeDomain={activeDomain} 
        setActiveDomain={setActiveDomain}
        selectedDocument={selectedDocument}
        setSelectedDocument={setSelectedDocument}
      />
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<DashboardPage activeDomain={activeDomain} />} />
          <Route path="/chat" element={
            <ChatPage activeDomain={activeDomain} setActiveDomain={setActiveDomain} />
          } />
          <Route path="/chat/:domainId" element={
            <ChatPage activeDomain={activeDomain} setActiveDomain={setActiveDomain} />
          } />
        </Routes>
      </div>
      
      {/* Document Viewer Panel — slides in when a document is selected */}
      {selectedDocument && (
        <DocumentViewer 
          document={selectedDocument} 
          onClose={() => setSelectedDocument(null)} 
        />
      )}
    </div>
  )
}

export default App
