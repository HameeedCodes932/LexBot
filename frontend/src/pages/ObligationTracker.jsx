import { useState, useEffect } from 'react'
import {
  ListChecks, Loader2, FileText, Clock, AlertTriangle,
  CheckCircle2, Circle, Trash2, ChevronDown,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import {
  getDocuments, extractObligations, getObligations,
  updateObligationStatus, deleteObligation,
} from '../api'

const STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400', icon: Circle },
  completed: { label: 'Completed', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', icon: CheckCircle2 },
  overdue: { label: 'Overdue', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: AlertTriangle },
}

const TYPE_COLORS = {
  payment: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  delivery: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  reporting: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  compliance: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
}

export default function ObligationTracker() {
  const [documents, setDocuments] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [obligations, setObligations] = useState([])
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(() => {
    getDocuments(1, 100).then((d) => setDocuments(d.items || [])).catch(() => {})
    loadObligations()
  }, [])

  const loadObligations = async (sf, tf) => {
    setLoading(true)
    try {
      const data = await getObligations(sf || statusFilter || null, tf || typeFilter || null)
      setObligations(data)
    } catch {
      toast.error('Failed to load obligations')
    } finally {
      setLoading(false)
    }
  }

  const handleExtract = async () => {
    if (!selectedDoc) { toast.error('Select a document'); return }
    setExtracting(true)
    try {
      const data = await extractObligations(selectedDoc)
      toast.success(`Found ${data.obligations_found} obligations`)
      loadObligations()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Extraction failed')
    } finally {
      setExtracting(false)
    }
  }

  const handleStatusChange = async (id, newStatus) => {
    try {
      await updateObligationStatus(id, newStatus)
      setObligations((prev) => prev.map((o) => o.id === id ? { ...o, status: newStatus } : o))
      toast.success('Status updated')
    } catch {
      toast.error('Failed to update status')
    }
  }

  const handleDelete = async (id) => {
    try {
      await deleteObligation(id)
      setObligations((prev) => prev.filter((o) => o.id !== id))
      toast.success('Obligation deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const counts = {
    total: obligations.length,
    pending: obligations.filter((o) => o.status === 'pending').length,
    completed: obligations.filter((o) => o.status === 'completed').length,
    overdue: obligations.filter((o) => o.status === 'overdue').length,
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0">
        <WorkspaceTopBar />
        <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-amber-400 flex items-center justify-center">
              <ListChecks size={20} className="text-navy-900" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Obligation Tracker</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Extract and track contractual obligations and deadlines</p>
            </div>
          </div>

          {/* Stats cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Total', value: counts.total, color: 'border-gray-300 dark:border-navy-600' },
              { label: 'Pending', value: counts.pending, color: 'border-amber-300 dark:border-amber-700' },
              { label: 'Completed', value: counts.completed, color: 'border-emerald-300 dark:border-emerald-700' },
              { label: 'Overdue', value: counts.overdue, color: 'border-red-300 dark:border-red-700' },
            ].map(({ label, value, color }) => (
              <div key={label} className={`bg-white dark:bg-navy-800 rounded-xl border-l-4 ${color} p-4 shadow-sm`}>
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
              </div>
            ))}
          </div>

          {/* Extract controls */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-5 mb-6 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Extract from Document</h3>
            <div className="flex gap-3">
              <select
                value={selectedDoc}
                onChange={(e) => setSelectedDoc(e.target.value)}
                className="flex-1 px-3 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400"
              >
                <option value="">Select document...</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.filename}>{d.filename}</option>
                ))}
              </select>
              <button
                onClick={handleExtract}
                disabled={!selectedDoc || extracting}
                className="px-5 py-2.5 bg-navy-900 hover:bg-navy-800 dark:bg-amber-400 dark:hover:bg-amber-500 dark:text-navy-900 text-white rounded-lg font-medium disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {extracting ? <Loader2 size={16} className="animate-spin" /> : <ListChecks size={16} />}
                {extracting ? 'Extracting...' : 'Extract'}
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); loadObligations(e.target.value, typeFilter) }}
              className="px-3 py-1.5 text-xs border border-gray-300 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-gray-700 dark:text-gray-300"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
              <option value="overdue">Overdue</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); loadObligations(statusFilter, e.target.value) }}
              className="px-3 py-1.5 text-xs border border-gray-300 dark:border-navy-600 rounded-lg bg-white dark:bg-navy-700 text-gray-700 dark:text-gray-300"
            >
              <option value="">All Types</option>
              <option value="payment">Payment</option>
              <option value="delivery">Delivery</option>
              <option value="reporting">Reporting</option>
              <option value="compliance">Compliance</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Obligations list */}
          {loading ? (
            <div className="text-center py-12">
              <Loader2 size={24} className="animate-spin text-gray-400 mx-auto" />
            </div>
          ) : obligations.length === 0 ? (
            <div className="text-center py-12 text-gray-400 dark:text-gray-500">
              <ListChecks size={48} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No obligations found. Extract from a document above.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {obligations.map((ob) => {
                const cfg = STATUS_CONFIG[ob.status] || STATUS_CONFIG.pending
                const StatusIcon = cfg.icon
                return (
                  <div
                    key={ob.id}
                    className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 dark:text-gray-100 font-medium leading-relaxed">
                          {ob.obligation_text}
                        </p>
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${cfg.color}`}>
                            <StatusIcon size={12} />
                            {cfg.label}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${TYPE_COLORS[ob.obligation_type] || TYPE_COLORS.other}`}>
                            {ob.obligation_type}
                          </span>
                          {ob.party_responsible && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              👤 {ob.party_responsible}
                            </span>
                          )}
                          {ob.deadline && ob.deadline !== 'Not specified' && (
                            <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                              <Clock size={12} />
                              {ob.deadline}
                            </span>
                          )}
                          {ob.source_document && (
                            <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                              <FileText size={12} />
                              {ob.source_document}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <select
                          value={ob.status}
                          onChange={(e) => handleStatusChange(ob.id, e.target.value)}
                          className="text-xs bg-gray-100 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 rounded-lg px-2 py-1 text-gray-600 dark:text-gray-400"
                        >
                          <option value="pending">Pending</option>
                          <option value="completed">Completed</option>
                          <option value="overdue">Overdue</option>
                        </select>
                        <button
                          onClick={() => handleDelete(ob.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
