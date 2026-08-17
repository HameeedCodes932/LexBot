import { useState, useEffect } from 'react'
import { Users, FileText, MessageSquare, Clock, Calendar, Search, Shield, XCircle, Scale } from 'lucide-react'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import { getAdminAnalytics, getAdminUsers, deactivateUser } from '../api'
import { StatCardSkeleton } from '../components/LoadingSkeleton'

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [analytics, setAnalytics] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [deactivating, setDeactivating] = useState(null)

  useEffect(() => {
    Promise.all([getAdminAnalytics(), getAdminUsers()])
      .then(([a, u]) => {
        setAnalytics(a)
        setUsers(Array.isArray(u) ? u : (u?.items || []))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleDeactivate = async (userId) => {
    setDeactivating(userId)
    try {
      await deactivateUser(userId)
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: 0 } : u))
      )
    } catch (err) {
      console.error(err)
    } finally {
      setDeactivating(null)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <WorkspaceTopBar title="Admin Dashboard" />

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {loading ? (
              <>
                {[1,2,3,4,5,6,7].map((i) => <StatCardSkeleton key={i} />)}
              </>
            ) : (
              <>
                <StatCard icon={Users} label="Total Users" value={analytics?.total_users || 0} color="bg-navy-800" />
                <StatCard icon={FileText} label="Total Documents" value={analytics?.total_documents || 0} color="bg-amber-500" />
                <StatCard icon={MessageSquare} label="Total Queries" value={analytics?.total_queries || 0} color="bg-gray-600" />
                <StatCard icon={Clock} label="Avg Response" value={`${analytics?.avg_response_time_ms || 0}ms`} color="bg-amber-700" />
                <StatCard icon={Calendar} label="Queries Today" value={analytics?.queries_today || 0} color="bg-navy-900" />
                <StatCard icon={Search} label="Clause Extractions" value={analytics?.total_clause_extractions || 0} color="bg-gray-700" />
                <StatCard icon={Scale} label="Comparisons" value={analytics?.total_comparisons || 0} color="bg-amber-600" />
              </>
            )}
          </div>

          {/* Top Questions */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Top 5 Questions</h3>
            {loading ? (
              <div className="space-y-2">
                {[1,2,3,4,5].map((i) => (
                  <div key={i} className="h-6 bg-gray-200 dark:bg-navy-700 rounded animate-pulse" />
                ))}
              </div>
            ) : analytics?.top_questions?.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-navy-700">
                    <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Question</th>
                    <th className="text-right py-2 font-medium text-gray-500 dark:text-gray-400">Frequency</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.top_questions.map((q, i) => (
                    <tr key={i} className="border-b border-gray-100 dark:border-navy-700/50">
                      <td className="py-2 text-gray-700 dark:text-gray-300 max-w-md truncate">{q.question}</td>
                      <td className="py-2 text-right text-gray-700 dark:text-gray-300">{q.frequency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">No data yet.</p>
            )}
          </div>

          {/* Most Searched Clause Types */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Most Searched Clause Types</h3>
            {loading ? (
              <div className="space-y-2">
                {[1,2,3,4,5].map((i) => (
                  <div key={i} className="h-6 bg-gray-200 dark:bg-navy-700 rounded animate-pulse" />
                ))}
              </div>
            ) : analytics?.most_searched_clause_types?.length > 0 ? (
              <ol className="space-y-1">
                {analytics.most_searched_clause_types.map((item, i) => (
                  <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white text-xs flex items-center justify-center font-medium">
                      {i + 1}
                    </span>
                    {item.clause_type} — {item.frequency} search(es)
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-gray-400 dark:text-gray-500">No data yet.</p>
            )}
          </div>

          {/* Users Table */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Users</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-navy-700">
                    <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Username</th>
                    <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Email</th>
                    <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Role</th>
                    <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Firm</th>
                    <th className="text-center py-2 font-medium text-gray-500 dark:text-gray-400">Active</th>
                    <th className="text-right py-2 font-medium text-gray-500 dark:text-gray-400">Docs</th>
                    <th className="text-right py-2 font-medium text-gray-500 dark:text-gray-400">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    [1,2,3,4,5].map((i) => (
                      <tr key={i}>
                        {[1,2,3,4,5,6,7].map((j) => (
                          <td key={j} className="py-2 px-1">
                            <div className="h-5 bg-gray-200 dark:bg-navy-700 rounded animate-pulse" />
                          </td>
                        ))}
                      </tr>
                    ))
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="border-b border-gray-100 dark:border-navy-700/50">
                        <td className="py-2 font-medium text-gray-900 dark:text-white">{u.username}</td>
                        <td className="py-2 text-gray-600 dark:text-gray-400">{u.email}</td>
                        <td className="py-2 text-gray-600 dark:text-gray-400 capitalize">{u.role}</td>
                        <td className="py-2 text-gray-600 dark:text-gray-400">{u.firm_name || '—'}</td>
                        <td className="py-2 text-center">
                          {u.is_active ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400">
                              Inactive
                            </span>
                          )}
                        </td>
                        <td className="py-2 text-right text-gray-600 dark:text-gray-400">{u.document_count || 0}</td>
                        <td className="py-2 text-right">
                          {u.is_active ? (
                            <button
                              onClick={() => handleDeactivate(u.id)}
                              disabled={deactivating === u.id}
                              className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium disabled:opacity-50 flex items-center gap-1 ml-auto"
                            >
                              {deactivating === u.id ? (
                                <>
                                  <div className="animate-spin rounded-full h-3 w-3 border-2 border-red-600 border-t-transparent" />
                                  Deactivating...
                                </>
                              ) : (
                                <>
                                  <XCircle size={14} />
                                  Deactivate
                                </>
                              )}
                            </button>
                          ) : (
                            <span className="text-xs text-gray-400 dark:text-gray-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
