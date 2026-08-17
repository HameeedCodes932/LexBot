import { useState, useEffect, useMemo, useCallback } from 'react'
import { MessageSquare, Plus, Trash2, X } from 'lucide-react'
import { clearMemory } from '../api'
import toast from 'react-hot-toast'

const GROUP_KEYS = ['Today', 'Yesterday', 'Earlier this week']

function groupLabel(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'Earlier'
  const now = new Date()
  const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const diff = Math.round((start(now) - start(d)) / 86400000)
  if (diff <= 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff < 7) return 'Earlier this week'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

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
    }, [setSessions])

  const updateStorage = (updated) => {
    setSessions(updated)
    localStorage.setItem('lexbot_sessions', JSON.stringify(updated))
  }

  const addCurrentSession = useCallback(() => {
    setSessions((prev) => {
      const exists = prev.find((s) => s.id === sessionId)
      if (exists) return prev
      const next = [
        { id: sessionId, label: `Session ${new Date().toLocaleDateString()}`, created_at: new Date().toISOString() },
        ...prev,
      ]
      localStorage.setItem('lexbot_sessions', JSON.stringify(next))
      return next
    })
  }, [sessionId, setSessions])

  useEffect(() => {
    if (sessionId) addCurrentSession()
  }, [sessionId, addCurrentSession])

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

  const grouped = useMemo(() => {
    const map = {}
    for (const s of sessions) {
      const g = groupLabel(s.created_at)
      if (!map[g]) map[g] = []
      map[g].push(s)
    }
    const groups = GROUP_KEYS.filter((k) => map[k]).map((k) => ({ label: k, items: map[k] }))
    const others = Object.keys(map)
      .filter((k) => !GROUP_KEYS.includes(k))
      .sort()
    others.forEach((k) => groups.push({ label: k, items: map[k] }))
    return groups
  }, [sessions])

  const listContent = (
    <div className="flex flex-col h-full bg-white dark:bg-navy-800">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-200 dark:border-navy-700">
        <h3 className="text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest">
          Conversations
        </h3>
        <div className="flex items-center gap-0.5">
          <button
            onClick={onNewSession}
            className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-white transition-colors"
            title="New session"
          >
            <Plus size={15} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-white transition-colors md:hidden"
            title="Close"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <button
        onClick={onNewSession}
        className="mx-3 mt-3 px-3 py-2 rounded-lg bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors flex items-center justify-center gap-1.5"
      >
        <Plus size={15} />
        New conversation
      </button>

      <div className="flex-1 overflow-y-auto scrollbar-thin py-2">
        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
            <MessageSquare size={20} className="mx-auto mb-2 opacity-50" />
            No conversations yet
          </div>
        ) : (
          grouped.map(({ label, items }) => (
            <div key={label} className="mb-1">
              <p className="px-4 py-1.5 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                {label}
              </p>
              {items.map((s) => (
                <div
                  key={s.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectSession(s.id)}
                  onKeyDown={(e) => e.key === 'Enter' && onSelectSession(s.id)}
                  className={`w-full flex items-center gap-2.5 px-4 py-2 text-left text-sm transition-colors hover:bg-gray-50 dark:hover:bg-navy-700/50 group cursor-pointer border-l-2 ${
                    s.id === sessionId
                      ? 'bg-amber-50 dark:bg-navy-700 text-navy-900 dark:text-white border-amber-400'
                      : 'text-gray-700 dark:text-gray-300 border-transparent'
                  }`}
                >
                  <MessageSquare size={13} className="flex-shrink-0 text-gray-400 dark:text-gray-500" />
                  <span className="flex-1 truncate">{s.label}</span>
                  <button
                    onClick={(e) => handleDelete(e, s.id)}
                    disabled={loading[s.id]}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 transition-all disabled:opacity-50"
                    title="Delete session"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={onClose} />
      )}
      {/* Desktop: in-flow column, collapses to zero width */}
      <aside
        className={`hidden md:block md:h-screen shrink-0 overflow-hidden bg-white dark:bg-navy-800 transition-[width] duration-200 ${
          isOpen ? 'w-72 border-r border-gray-200 dark:border-navy-700' : 'w-0 border-transparent'
        }`}
      >
        <div className="w-72 h-full">{listContent}</div>
      </aside>
      {/* Mobile: overlay drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-72 transform transition-transform duration-200 md:hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {listContent}
      </aside>
    </>
  )
}
