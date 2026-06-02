import { useState, useEffect } from 'react'
import {
  Library, Loader2, Trash2, Star, StarOff, Search,
  FileText, Filter, Plus,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { getClauses, deleteClause, toggleBenchmark, saveClause } from '../api'

const CLAUSE_TYPES = [
  'indemnification', 'termination', 'payment', 'liability',
  'confidentiality', 'governing-law', 'dispute-resolution',
  'warranty', 'intellectual-property', 'force-majeure',
]

export default function ClauseLibrary() {
  const [clauses, setClauses] = useState([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('')
  const [benchmarksOnly, setBenchmarksOnly] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [newClause, setNewClause] = useState({
    clause_type: 'indemnification', title: '', content: '', source_document: '', notes: '',
  })

  const loadClauses = async () => {
    setLoading(true)
    try {
      const data = await getClauses(typeFilter || null, benchmarksOnly)
      setClauses(data)
    } catch {
      toast.error('Failed to load clauses')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadClauses() }, [typeFilter, benchmarksOnly])

  const handleDelete = async (id) => {
    try {
      await deleteClause(id)
      setClauses((prev) => prev.filter((c) => c.id !== id))
      toast.success('Clause deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const handleToggleBenchmark = async (id) => {
    try {
      const data = await toggleBenchmark(id)
      setClauses((prev) => prev.map((c) => c.id === id ? { ...c, is_benchmark: data.is_benchmark } : c))
      toast.success(data.is_benchmark ? 'Marked as benchmark' : 'Benchmark removed')
    } catch {
      toast.error('Failed to update')
    }
  }

  const handleSave = async () => {
    if (!newClause.content.trim()) { toast.error('Content is required'); return }
    try {
      await saveClause(
        newClause.clause_type, newClause.content, newClause.title,
        newClause.source_document, newClause.notes,
      )
      toast.success('Clause saved')
      setShowAdd(false)
      setNewClause({ clause_type: 'indemnification', title: '', content: '', source_document: '', notes: '' })
      loadClauses()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save')
    }
  }

  const filtered = clauses.filter((c) => {
    if (searchTerm) {
      const lower = searchTerm.toLowerCase()
      return (
        c.content.toLowerCase().includes(lower) ||
        c.title.toLowerCase().includes(lower) ||
        c.source_document.toLowerCase().includes(lower)
      )
    }
    return true
  })

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
                <Library size={20} className="text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Clause Library</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Save, search, and benchmark contract clauses</p>
              </div>
            </div>
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-rose-600 to-pink-600 text-white rounded-lg font-medium hover:from-rose-700 hover:to-pink-700 transition-all text-sm"
            >
              <Plus size={16} />
              Add Clause
            </button>
          </div>

          {/* Add clause form */}
          {showAdd && (
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5 mb-6 shadow-sm animate-fade-in">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Add New Clause</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Clause Type</label>
                  <select
                    value={newClause.clause_type}
                    onChange={(e) => setNewClause({ ...newClause, clause_type: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100"
                  >
                    {CLAUSE_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replace('-', ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Title</label>
                  <input
                    value={newClause.title}
                    onChange={(e) => setNewClause({ ...newClause, title: e.target.value })}
                    placeholder="e.g., Strong indemnification clause"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>
              <div className="mb-3">
                <label className="block text-xs text-gray-500 mb-1">Clause Content *</label>
                <textarea
                  value={newClause.content}
                  onChange={(e) => setNewClause({ ...newClause, content: e.target.value })}
                  rows={4}
                  placeholder="Paste the clause text here..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 resize-none"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Source Document</label>
                  <input
                    value={newClause.source_document}
                    onChange={(e) => setNewClause({ ...newClause, source_document: e.target.value })}
                    placeholder="Original filename"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Notes</label>
                  <input
                    value={newClause.notes}
                    onChange={(e) => setNewClause({ ...newClause, notes: e.target.value })}
                    placeholder="Why is this notable?"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={handleSave} className="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 transition-colors">Save</button>
                <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-navy-600 rounded-lg text-sm hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors">Cancel</button>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex gap-3 mb-6 flex-wrap items-center">
            <div className="flex-1 min-w-[200px] relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search clauses..."
                className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-gray-700 dark:text-gray-300"
            >
              <option value="">All Types</option>
              {CLAUSE_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace('-', ' ')}</option>
              ))}
            </select>
            <button
              onClick={() => setBenchmarksOnly(!benchmarksOnly)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border transition-colors ${
                benchmarksOnly
                  ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400'
                  : 'border-gray-300 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:border-amber-300'
              }`}
            >
              <Star size={14} />
              Benchmarks
            </button>
          </div>

          {/* Clauses list */}
          {loading ? (
            <div className="text-center py-12">
              <Loader2 size={24} className="animate-spin text-gray-400 mx-auto" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-gray-400 dark:text-gray-500">
              <Library size={48} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No clauses saved yet. Extract and save from the Clause Extractor.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filtered.map((clause) => (
                <div
                  key={clause.id}
                  className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="px-5 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {clause.is_benchmark && <Star size={14} className="text-amber-500 fill-amber-500" />}
                          <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                            {clause.title || `${clause.clause_type} clause`}
                          </h4>
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-400 capitalize">
                            {clause.clause_type.replace('-', ' ')}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-3">
                          {clause.content}
                        </p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                          {clause.source_document && (
                            <span className="flex items-center gap-1">
                              <FileText size={12} />
                              {clause.source_document}
                            </span>
                          )}
                          {clause.notes && <span>📝 {clause.notes}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button
                          onClick={() => handleToggleBenchmark(clause.id)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            clause.is_benchmark
                              ? 'text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                              : 'text-gray-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                          }`}
                          title={clause.is_benchmark ? 'Remove benchmark' : 'Set as benchmark'}
                        >
                          {clause.is_benchmark ? <Star size={16} className="fill-current" /> : <StarOff size={16} />}
                        </button>
                        <button
                          onClick={() => handleDelete(clause.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
