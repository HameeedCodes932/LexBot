import { useState, useEffect } from 'react'
import { getOrgAuditLogs } from '../api'
import Navbar from '../components/Navbar'
import { History, Search, Calendar, Shield, Info, ArrowLeft, ArrowRight, User } from 'lucide-react'

export default function AuditLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [error, setError] = useState(null)
  const [selectedLog, setSelectedLog] = useState(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const data = await getOrgAuditLogs(page, 20)
      setLogs(data)
    } catch (err) {
      setError('Failed to fetch audit logs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [page])

  return (
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      <Navbar />

      <main className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <History className="text-blue-500 h-8 w-8" />
            Audit Logging
          </h1>
          <p className="text-slate-400 mt-1">Review full administrative activity history for security compliance and tracking.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Logs Table */}
          <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-xl flex flex-col min-h-[500px]">
            <div className="p-6 border-b border-slate-700/50 flex justify-between items-center">
              <h2 className="text-xl font-bold text-white">Activity History</h2>
            </div>

            {loading ? (
              <div className="flex-1 flex justify-center items-center p-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
              </div>
            ) : logs.length === 0 ? (
              <div className="flex-1 flex justify-center items-center p-12 text-slate-500">No audit logs found.</div>
            ) : (
              <div className="flex-1 flex flex-col justify-between">
                <div className="divide-y divide-slate-700/50">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className={`p-4 flex items-center justify-between gap-4 hover:bg-slate-800/40 transition-all cursor-pointer ${
                        selectedLog?.id === log.id ? 'bg-slate-800/60 border-l-4 border-blue-500 pl-3' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Shield size={14} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-white truncate">{log.action}</p>
                          <p className="text-xs text-slate-400 truncate flex items-center gap-1 mt-0.5">
                            <User size={10} /> {log.email}
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-xs text-slate-500">
                          {new Date(log.created_at).toLocaleDateString()}
                        </span>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                <div className="p-4 border-t border-slate-700/50 flex justify-between items-center text-sm text-slate-400">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="flex items-center gap-1 hover:text-white transition-all disabled:opacity-30 disabled:hover:text-slate-400"
                  >
                    <ArrowLeft size={16} /> Prev
                  </button>
                  <span>Page {page}</span>
                  <button
                    disabled={logs.length < 20}
                    onClick={() => setPage((p) => p + 1)}
                    className="flex items-center gap-1 hover:text-white transition-all disabled:opacity-30 disabled:hover:text-slate-400"
                  >
                    Next <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Details Sidebar */}
          <div className="lg:col-span-1 bg-slate-800/50 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl h-fit">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
              <Info className="text-blue-500" size={20} />
              Log Details
            </h2>

            {selectedLog ? (
              <div className="space-y-5">
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Action</label>
                  <p className="text-white font-bold bg-slate-900 px-3 py-2 rounded-lg border border-slate-700 mt-1">{selectedLog.action}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Initiated By</label>
                  <p className="text-slate-200 mt-1 font-semibold">{selectedLog.username}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{selectedLog.email}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Timestamp</label>
                  <p className="text-slate-200 mt-1 flex items-center gap-1 text-sm">
                    <Calendar size={14} className="text-slate-400" />
                    {new Date(selectedLog.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedLog.ip_address && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">IP Address</label>
                    <p className="text-slate-200 mt-1 font-mono text-sm">{selectedLog.ip_address}</p>
                  </div>
                )}
                {selectedLog.user_agent && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">User Agent</label>
                    <p className="text-slate-300 mt-1 text-xs leading-relaxed bg-slate-900/50 p-2.5 rounded-lg border border-slate-700/30 max-h-[120px] overflow-y-auto font-mono">
                      {selectedLog.user_agent}
                    </p>
                  </div>
                )}
                {selectedLog.details && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Context Metadata</label>
                    <pre className="text-slate-300 mt-1 text-xs font-mono bg-slate-900 p-3 rounded-lg border border-slate-700 overflow-x-auto">
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-500 text-center py-12">
                Select a log entry from the list to view full security meta details.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
