import React from 'react'

function DocumentViewer({ document, onClose }) {
  if (!document) return null

  return (
    <div className="w-96 bg-white border-l border-slate-200 flex flex-col h-full shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-50">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm">📄</span>
          <span className="text-sm font-medium text-slate-800 truncate">{document.title || 'Untitled'}</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-sm px-2"
        >
          ×
        </button>
      </div>

      {/* Document info */}
      <div className="px-4 py-2 border-b border-slate-100 bg-slate-50/50">
        <div className="text-xs text-slate-500 flex items-center gap-2">
          <span className="px-1.5 py-0.5 bg-slate-200 rounded text-[10px]">{document.document_type || 'note'}</span>
          <span>v{document.version || 1}</span>
          <span>·</span>
          <span>{document.updated_at ? new Date(document.updated_at).toLocaleDateString() : 'Now'}</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="prose prose-sm max-w-none">
          {document.content ? (
            <div className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed">
              {document.content}
            </div>
          ) : (
            <div className="text-slate-400 text-sm italic">Empty document</div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-slate-200 bg-slate-50">
        <div className="text-[10px] text-slate-400 text-center">
          Click outside or × to close
        </div>
      </div>
    </div>
  )
}

export default DocumentViewer
