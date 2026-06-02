import { useState, useEffect } from 'react'
import { MessageSquare, Plus, Trash2, Clock, X } from 'lucide-react'
import { getMemory, clearMemory } from '../api'
import toast from 'react-hot-toast'

export default function ChatHistorySidebar({
  sessionId,
  onSelectSession,
  onNewSession,
  sessions,
  setSessions,
  isOpen,
  onClose,
}) {
  const [loading, setLoading] = useState({})

  useEffect(() => {
    const stored = localStorage.getItem('lexbot_sessions')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        setSessions(parsed)
      } catch {}
    }
  }, [])

  const updateStorage = (updated) => {
    setSessions(updated)
    localStorage.setItem('lexbot_sessions', JSON.stringify(updated))
  }

  const addCurrentSession = () => {
    const exists = sessions.find((s) => s.id === sessionId)
    if (!exists) {
      const updated = [
        { id: sessionId, label: `Session ${new Date().toLocaleDateString()}`, created_at: new Date().toISOString() },
        ...sessions,
      ]
      updateStorage(updated)
    }
  }

  useEffect(() => {
    if (sessionId) addCurrentSession()
  }, [sessionId])

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    setLoading((p) => ({ ...p, [id]: true }))
    try {
      await clearMemory(id)
      const updated = sessions.filter((s) => s.id !== id)
      updateStorage(updated)
      toast.success('Session deleted')
    } catch {
      toast.error('Failed to delete session')
    } finally {
      setLoading((p) => ({ ...p, [id]: false }))
    }
  }

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/30 z-20 md:hidden" onClick={onClose} />
      )}
      <aside
        className={`fixed md:relative inset-y-0 left-0 z-30 w-72 bg-white dark:bg-navy-800 border-r border-gray-200 dark:border-navy-700 flex flex-col transform transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-navy-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Sessions</h3>
          <div className="flex items-center gap-1">
            <button
              onClick={onNewSession}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors"
              title="New session"
            >
              <Plus size={16} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors md:hidden"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin py-2">
          {sessions.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
              <MessageSquare size={24} className="mx-auto mb-2 opacity-50" />
              No saved sessions
            </div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:bg-gray-50 dark:hover:bg-navy-700/50 group ${
                  s.id === sessionId
                    ? 'bg-navy-50 dark:bg-navy-700 text-navy-900 dark:text-white'
                    : 'text-gray-700 dark:text-gray-300'
                }`}
              >
                <MessageSquare size={14} className="flex-shrink-0 text-gray-400 dark:text-gray-500" />
                <span className="flex-1 truncate">{s.label}</span>
                <button
                  onClick={(e) => handleDelete(e, s.id)}
                  disabled={loading[s.id]}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 transition-all disabled:opacity-50"
                >
                  <Trash2 size={12} />
                </button>
              </button>
            ))
          )}
        </div>
      </aside>
    </>
  )
}
