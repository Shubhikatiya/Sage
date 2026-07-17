import React, { useState, useCallback } from 'react'
import { uploadAsset } from '../services/api_v4'

export default function AssetUploader({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [approvingId, setApprovingId] = useState(null)

  const approveAll = async (assetId) => {
    if (!assetId) return
    setApprovingId(assetId)
    try {
      const { approveAssetKnowledge } = await import('../services/api_v4')
      await approveAssetKnowledge(assetId, { approve_all: true })
      setUploads(prev => prev.map(u => 
        u.result?.asset?.id === assetId 
          ? { ...u, approved: true }
          : u
      ))
    } catch (error) {
      console.error('Approval failed:', error)
      alert('Approval failed: ' + (error.response?.data?.errors?.[0]?.message || error.message))
    } finally {
      setApprovingId(null)
    }
  }

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(async (e) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    await processFiles(files)
  }, [])

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files)
    await processFiles(files)
  }

  const processFiles = async (files) => {
    setIsUploading(true)
    
    for (const file of files) {
      const uploadId = Date.now() + Math.random()
      
      setUploads(prev => [...prev, {
        id: uploadId,
        filename: file.name,
        status: 'uploading',
        progress: 0
      }])
      
      try {
        const response = await uploadAsset(file, true)
        const data = response.data.data
        
        setUploads(prev => prev.map(u => 
          u.id === uploadId 
            ? { ...u, status: 'complete', result: data }
            : u
        ))
        
        if (onUploadComplete) {
          onUploadComplete(data)
        }
      } catch (error) {
        setUploads(prev => prev.map(u => 
          u.id === uploadId 
            ? { ...u, status: 'error', error: error.message }
            : u
        ))
      }
    }
    
    setIsUploading(false)
  }

  const clearCompleted = () => {
    setUploads(prev => prev.filter(u => u.status === 'uploading'))
  }

  return (
    <div className="asset-uploader">
      <div 
        className={`upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-icon">📁</div>
        <p className="upload-text">
          {isUploading ? 'Uploading...' : 'Drag files here or click to browse'}
        </p>
        <p className="upload-hint">
          Supports: PDF, Images, Markdown, DOCX, ChatGPT/Claude JSON exports
        </p>
        <input
          type="file"
          multiple
          onChange={handleFileSelect}
          className="file-input"
          accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.md,.docx,.txt,.json,.mp3,.mp4,.py,.js,.ts,.html,.css"
        />
      </div>

      {uploads.length > 0 && (
        <div className="uploads-list">
          <div className="uploads-header">
            <h4>Uploads ({uploads.length})</h4>
            <button onClick={clearCompleted} className="clear-btn">
              Clear Completed
            </button>
          </div>
          
          {uploads.map(upload => (
            <div key={upload.id} className={`upload-item ${upload.status}`}>
              <div className="upload-info">
                <span className="filename">{upload.filename}</span>
                <span className={`status-badge ${upload.status}`}>
                  {upload.status === 'complete' ? '✓ Processed' : 
                   upload.status === 'error' ? '✗ Failed' : '⏳ Uploading...'}
                </span>
              </div>
              
              {upload.result && upload.result.extracted_knowledge && (
                <div className="extraction-results">
                  {/* Primary Document Node */}
                  {upload.result.extracted_knowledge.primary_node && (
                    <div className="primary-node">
                      <p className="node-label">📄 Document</p>
                      <p className="node-title">{upload.result.extracted_knowledge.primary_node.title}</p>
                      <div className="node-stats">
                        <span>{upload.result.extracted_knowledge.stats?.total_words || 0} words</span>
                        <span>{upload.result.extracted_knowledge.stats?.extracted_items || 0} insights</span>
                      </div>
                      
                      {/* Full text preview - expandable */}
                      <details className="full-text-preview">
                        <summary>View full document text ({upload.result.extraction?.text_length || 0} chars)</summary>
                        <pre className="document-content">
                          {upload.result.extracted_knowledge.primary_node.content}
                        </pre>
                      </details>
                      
                      {/* Summary */}
                      {upload.result.extracted_knowledge.summary && (
                        <div className="document-summary">
                          <p className="summary-label">Summary:</p>
                          <p>{upload.result.extracted_knowledge.summary}</p>
                        </div>
                      )}
                      
                      {/* Key Themes */}
                      {upload.result.extracted_knowledge.key_themes?.length > 0 && (
                        <div className="key-themes">
                          <p className="themes-label">Key Themes:</p>
                          <div className="themes-list">
                            {upload.result.extracted_knowledge.key_themes.slice(0, 10).map((theme, i) => (
                              <span key={i} className="theme-tag">{theme}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Child Nodes - Extracted Insights */}
                  {upload.result.extracted_knowledge.child_nodes?.length > 0 && (
                    <div className="child-nodes">
                      <p className="nodes-label">
                        🧠 Extracted Insights ({upload.result.extracted_knowledge.child_nodes.length})
                      </p>
                      <div className="insights-list">
                        {upload.result.extracted_knowledge.child_nodes.slice(0, 5).map((child, i) => (
                          <div key={i} className={`insight-item ${child.node_type}`}>
                            <span className="insight-type">{child.node_type}</span>
                            <span className="insight-title">{child.title}</span>
                            <span className="insight-confidence">
                              {Math.round(child.confidence * 100)}%
                            </span>
                          </div>
                        ))}
                        {upload.result.extracted_knowledge.child_nodes.length > 5 && (
                          <p className="more-insights">
                            +{upload.result.extracted_knowledge.child_nodes.length - 5} more insights
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Stats */}
                  {upload.result.extracted_knowledge.stats && (
                    <div className="extraction-stats">
                      <span>📊 {upload.result.extracted_knowledge.stats.decisions} decisions</span>
                      <span>💡 {upload.result.extracted_knowledge.stats.insights} insights</span>
                      <span>❓ {upload.result.extracted_knowledge.stats.questions} questions</span>
                      <span>✅ {upload.result.extracted_knowledge.stats.tasks} tasks</span>
                      <span>🎯 {upload.result.extracted_knowledge.stats.concepts} concepts</span>
                    </div>
                  )}
                  
                  {/* Approve button */}
                  <button 
                    className="approve-btn"
                    disabled={!!approvingId || upload.approved}
                    onClick={() => {
                      if (upload.result.asset?.id) {
                        approveAll(upload.result.asset.id)
                      }
                    }}
                  >
                    {approvingId === upload.result.asset?.id 
                      ? 'Approving...' 
                      : upload.approved 
                        ? 'Approved' 
                        : `Approve All (${upload.result.extracted_knowledge.child_nodes?.length || 0} insights)`}
                  </button>
                </div>
              )}
              
              {upload.error && (
                <p className="error-message">{upload.error}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .asset-uploader {
          padding: 1rem;
        }
        
        .upload-zone {
          border: 2px dashed #e2e8f0;
          border-radius: 12px;
          padding: 2rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
          background: #f8fafc;
          position: relative;
        }
        
        .upload-zone:hover {
          border-color: #3b82f6;
          background: #eff6ff;
        }
        
        .upload-zone.dragging {
          border-color: #3b82f6;
          background: #dbeafe;
          transform: scale(1.02);
        }
        
        .upload-zone.uploading {
          opacity: 0.7;
          cursor: wait;
        }
        
        .upload-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }
        
        .upload-text {
          font-size: 1.1rem;
          color: #1e293b;
          margin: 0 0 0.5rem;
        }
        
        .upload-hint {
          font-size: 0.85rem;
          color: #64748b;
          margin: 0;
        }
        
        .file-input {
          position: absolute;
          inset: 0;
          opacity: 0;
          cursor: pointer;
        }
        
        .uploads-list {
          margin-top: 1.5rem;
        }
        
        .uploads-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.75rem;
        }
        
        .uploads-header h4 {
          margin: 0;
          font-size: 0.9rem;
          color: #475569;
        }
        
        .clear-btn {
          background: none;
          border: none;
          color: #3b82f6;
          cursor: pointer;
          font-size: 0.8rem;
        }
        
        .upload-item {
          background: white;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 0.75rem;
          margin-bottom: 0.5rem;
        }
        
        .upload-item.complete {
          border-color: #22c55e;
        }
        
        .upload-item.error {
          border-color: #ef4444;
        }
        
        .upload-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .filename {
          font-size: 0.9rem;
          color: #1e293b;
          font-weight: 500;
        }
        
        .status-badge {
          font-size: 0.75rem;
          padding: 0.25rem 0.5rem;
          border-radius: 9999px;
          font-weight: 500;
        }
        
        .status-badge.complete {
          background: #dcfce7;
          color: #166534;
        }
        
        .status-badge.error {
          background: #fee2e2;
          color: #991b1b;
        }
        
        .status-badge.uploading {
          background: #fef3c7;
          color: #92400e;
        }
        
        .extraction-results {
          margin-top: 0.75rem;
          padding-top: 0.75rem;
          border-top: 1px solid #e2e8f0;
        }
        
        .primary-node {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 1rem;
          margin-bottom: 1rem;
        }
        
        .node-label {
          font-size: 0.75rem;
          text-transform: uppercase;
          color: #64748b;
          font-weight: 600;
          margin: 0 0 0.25rem;
        }
        
        .node-title {
          font-size: 1rem;
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 0.5rem;
        }
        
        .node-stats {
          display: flex;
          gap: 1rem;
          font-size: 0.8rem;
          color: #64748b;
          margin-bottom: 0.75rem;
        }
        
        .full-text-preview {
          margin-bottom: 0.75rem;
        }
        
        .full-text-preview summary {
          cursor: pointer;
          color: #3b82f6;
          font-size: 0.85rem;
          font-weight: 500;
        }
        
        .document-content {
          max-height: 300px;
          overflow-y: auto;
          background: #1e293b;
          color: #e2e8f0;
          padding: 1rem;
          border-radius: 6px;
          font-size: 0.8rem;
          line-height: 1.6;
          white-space: pre-wrap;
          word-wrap: break-word;
          margin-top: 0.5rem;
        }
        
        .document-summary {
          background: #eff6ff;
          border-left: 3px solid #3b82f6;
          padding: 0.75rem;
          border-radius: 0 6px 6px 0;
          margin-bottom: 0.75rem;
        }
        
        .summary-label {
          font-weight: 600;
          color: #1e40af;
          margin: 0 0 0.25rem;
          font-size: 0.85rem;
        }
        
        .document-summary p {
          margin: 0;
          color: #475569;
          font-size: 0.85rem;
        }
        
        .key-themes {
          margin-bottom: 0.75rem;
        }
        
        .themes-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: #475569;
          margin: 0 0 0.25rem;
        }
        
        .themes-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }
        
        .theme-tag {
          font-size: 0.75rem;
          padding: 0.2rem 0.5rem;
          background: #f1f5f9;
          border-radius: 9999px;
          color: #475569;
        }
        
        .child-nodes {
          margin-bottom: 0.75rem;
        }
        
        .nodes-label {
          font-size: 0.9rem;
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 0.5rem;
        }
        
        .insights-list {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }
        
        .insight-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.4rem 0.6rem;
          border-radius: 6px;
          font-size: 0.85rem;
        }
        
        .insight-item.decision {
          background: #fef3c7;
        }
        
        .insight-item.insight {
          background: #dbeafe;
        }
        
        .insight-item.question {
          background: #fce7f3;
        }
        
        .insight-item.task {
          background: #e0e7ff;
        }
        
        .insight-item.concept {
          background: #f3e8ff;
        }
        
        .insight-type {
          font-size: 0.7rem;
          text-transform: uppercase;
          font-weight: 700;
          min-width: 60px;
        }
        
        .insight-title {
          flex: 1;
          color: #1e293b;
        }
        
        .insight-confidence {
          font-size: 0.75rem;
          color: #64748b;
        }
        
        .more-insights {
          font-size: 0.8rem;
          color: #64748b;
          text-align: center;
          margin: 0.25rem 0;
        }
        
        .extraction-stats {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
        }
        
        .extraction-stats span {
          font-size: 0.8rem;
          padding: 0.25rem 0.5rem;
          background: #f1f5f9;
          border-radius: 4px;
          color: #475569;
        }
        
        .approve-btn {
          width: 100%;
          padding: 0.6rem;
          background: #3b82f6;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s;
        }
        
        .approve-btn:hover {
          background: #2563eb;
        }
        
        .error-message {
          font-size: 0.8rem;
          color: #ef4444;
          margin: 0.5rem 0 0;
        }
      `}</style>
    </div>
  )
}

async function approveAll(assetId) {
  try {
    const formData = new FormData()
    formData.append('approve_all', 'true')
    
    const response = await fetch(`http://localhost:8020/api/asset/${assetId}/approve`, {
      method: 'POST',
      body: formData
    })
    const result = await response.json()
    const data = result.data || result
    alert(`Approved ${data.approved || 0} nodes into knowledge graph!`)
  } catch (e) {
    alert('Failed to approve: ' + e.message)
  }
}
