import { useState, useEffect } from 'react'
import { X, FileText, Loader2 } from 'lucide-react'

export default function DocumentViewer({ filename, content, onClose }) {
  const [tab, setTab] = useState('preview')
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState(content || '')

  useEffect(() => {
    if (content) {
      setText(content)
      return
    }
  }, [content])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl w-full max-w-3xl mx-4 max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-navy-700">
          <div className="flex items-center gap-2 min-w-0">
            <FileText size={16} className="text-gray-400 flex-shrink-0" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{filename}</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-gray-400" />
            </div>
          ) : (
            <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
              {text || 'No preview available.'}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
