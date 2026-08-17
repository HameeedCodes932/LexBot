import { useState, useEffect } from 'react'
import { getOrgAuditLogs } from '../api'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import { History, Calendar, Shield, Info, ArrowLeft, ArrowRight, User } from 'lucide-react'

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
    <div className="flex min-h-screen bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-gray-100">
      <Navbar />

      <div className="flex-1 flex flex-col min-w-0">
        <WorkspaceTopBar />

        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-400 flex items-center justify-center">
              <History className="text-navy-900 h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-navy-900 dark:text-white">
              Audit Logging
            </h1>
          </div>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Review full administrative activity history for security compliance and tracking.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Logs Table */}
          <div className="lg:col-span-2 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-xl overflow-hidden shadow-sm flex flex-col min-h-[500px]">
            <div className="p-6 border-b border-gray-200 dark:border-navy-700 flex justify-between items-center">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Activity History</h2>
            </div>

            {loading ? (
              <div className="flex-1 flex justify-center items-center p-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-navy-900 dark:border-amber-400 border-t-transparent" />
              </div>
            ) : logs.length === 0 ? (
              <div className="flex-1 flex justify-center items-center p-12 text-gray-400 dark:text-gray-500">No audit logs found.</div>
            ) : (
              <div className="flex-1 flex flex-col justify-between">
                <div className="divide-y divide-gray-100 dark:divide-navy-700">
                  {logs.map((log) => (
                    <div
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className={`p-4 flex items-center justify-between gap-4 hover:bg-gray-50 dark:hover:bg-navy-700/40 transition-colors cursor-pointer ${
                        selectedLog?.id === log.id ? 'bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 pl-3' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Shield size={14} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-navy-900 dark:text-white truncate">{log.action}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate flex items-center gap-1 mt-0.5">
                            <User size={10} /> {log.email}
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(log.created_at).toLocaleDateString()}
                        </span>
                        <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">
                          {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                <div className="p-4 border-t border-gray-200 dark:border-navy-700 flex justify-between items-center text-sm text-gray-500 dark:text-gray-400">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="flex items-center gap-1 hover:text-navy-900 dark:hover:text-white transition-colors disabled:opacity-30 disabled:hover:text-gray-500 dark:disabled:hover:text-gray-400"
                  >
                    <ArrowLeft size={16} /> Prev
                  </button>
                  <span>Page {page}</span>
                  <button
                    disabled={logs.length < 20}
                    onClick={() => setPage((p) => p + 1)}
                    className="flex items-center gap-1 hover:text-navy-900 dark:hover:text-white transition-colors disabled:opacity-30 disabled:hover:text-gray-500 dark:disabled:hover:text-gray-400"
                  >
                    Next <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Details Sidebar */}
          <div className="lg:col-span-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 p-6 rounded-xl shadow-sm h-fit">
            <h2 className="text-lg font-semibold text-navy-900 dark:text-white mb-6 flex items-center gap-2">
              <Info className="text-amber-600 dark:text-amber-400" size={18} />
              Log Details
            </h2>

            {selectedLog ? (
              <div className="space-y-5">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Action</label>
                  <p className="text-navy-900 dark:text-white font-semibold bg-gray-50 dark:bg-navy-900 px-3 py-2 rounded-lg border border-gray-200 dark:border-navy-600 mt-1">{selectedLog.action}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Initiated By</label>
                  <p className="text-navy-900 dark:text-gray-100 mt-1 font-medium">{selectedLog.username}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{selectedLog.email}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Timestamp</label>
                  <p className="text-navy-900 dark:text-gray-100 mt-1 flex items-center gap-1 text-sm">
                    <Calendar size={14} className="text-gray-400" />
                    {new Date(selectedLog.created_at).toLocaleString()}
                  </p>
                </div>
                {selectedLog.ip_address && (
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">IP Address</label>
                    <p className="text-navy-900 dark:text-gray-100 mt-1 font-mono text-sm">{selectedLog.ip_address}</p>
                  </div>
                )}
                {selectedLog.user_agent && (
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">User Agent</label>
                    <p className="text-gray-700 dark:text-gray-300 mt-1 text-xs leading-relaxed bg-gray-50 dark:bg-navy-900 p-2.5 rounded-lg border border-gray-200 dark:border-navy-600 max-h-[120px] overflow-y-auto font-mono">
                      {selectedLog.user_agent}
                    </p>
                  </div>
                )}
                {selectedLog.details && (
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Context Metadata</label>
                    <pre className="text-gray-700 dark:text-gray-300 mt-1 text-xs font-mono bg-gray-50 dark:bg-navy-900 p-3 rounded-lg border border-gray-200 dark:border-navy-600 overflow-x-auto">
                      {JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-400 dark:text-gray-500 text-center py-12">
                Select a log entry from the list to view full security meta details.
              </div>
            )}
          </div>
        </div>
      </main>
      </div>
    </div>
  )
}
