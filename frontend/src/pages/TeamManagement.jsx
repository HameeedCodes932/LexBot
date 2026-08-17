import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getMembers, inviteMember, removeMember, updateMemberRole, leaveOrg } from '../api'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import { Users, UserPlus, Trash2, ShieldAlert, LogOut, CheckCircle, Clock } from 'lucide-react'

export default function TeamManagement() {
  const { user, isOrgAdmin, isOrgOwner, logout, setUser } = useAuth()
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const fetchMembers = async () => {
    try {
      setLoading(true)
      const data = await getMembers()
      setMembers(data)
    } catch (err) {
      setError('Failed to fetch team members.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMembers()
  }, [])

  const handleInvite = async (e) => {
    e.preventDefault()
    if (!inviteEmail) return
    try {
      setInviteLoading(true)
      setMessage(null)
      setError(null)
      await inviteMember(inviteEmail, inviteRole)
      setMessage(`Invitation successfully sent to ${inviteEmail}.`)
      setInviteEmail('')
      fetchMembers()
    } catch (err) {
      const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : detail?.message || 'Failed to send invitation.')
    } finally {
      setInviteLoading(false)
    }
  }

  const handleRoleChange = async (memberUserId, newRole) => {
    try {
      setError(null)
      await updateMemberRole(memberUserId, newRole)
      setMessage('Role updated successfully.')
      fetchMembers()
    } catch (err) {
      const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : detail?.message || 'Failed to change role.')
    }
  }

  const handleRemove = async (memberUserId) => {
    if (!window.confirm('Are you sure you want to remove this member?')) return
    try {
      setError(null)
      await removeMember(memberUserId)
      setMessage('Member removed successfully.')
      fetchMembers()
    } catch (err) {
      const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : detail?.message || 'Failed to remove member.')
    }
  }

  const handleLeave = async () => {
    if (!window.confirm('Are you sure you want to leave this organization? This action cannot be undone.')) return
    try {
      setError(null)
      await leaveOrg()
      alert('You have left the organization.')
      // Refresh context
      setUser({ ...user, org_id: null, org_role: null, org_name: null })
      logout()
    } catch (err) {
      const detail = err.response?.data?.detail; setError(typeof detail === 'string' ? detail : detail?.message || 'Failed to leave organization.')
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-gray-100">
      <Navbar />

      <div className="flex-1 flex flex-col min-w-0">
        <WorkspaceTopBar />

        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-6xl mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-400 flex items-center justify-center">
                <Users className="text-navy-900 h-5 w-5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-navy-900 dark:text-white">
                Team Management
              </h1>
            </div>
            <p className="text-gray-500 dark:text-gray-400 mt-2">Manage firm workspaces, invite colleagues, and control roles.</p>
          </div>
          {!isOrgOwner && (
            <button
              onClick={handleLeave}
              className="flex items-center gap-2 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20 px-4 py-2 rounded-lg transition-colors font-medium"
            >
              <LogOut size={16} />
              Leave Workspace
            </button>
          )}
        </div>

        {/* Notifications */}
        {message && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 flex items-center gap-3 animate-fade-in">
            <CheckCircle size={20} />
            <span>{message}</span>
          </div>
        )}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 flex items-center gap-3 animate-fade-in">
            <ShieldAlert size={20} />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Invite Box */}
          {isOrgAdmin && (
            <div className="lg:col-span-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 p-6 rounded-xl shadow-sm h-fit">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white mb-4 flex items-center gap-2">
                <UserPlus className="text-amber-600 dark:text-amber-400" size={18} />
                Invite Colleague
              </h2>
              <form onSubmit={handleInvite} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Email Address</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                    placeholder="colleague@firm.com"
                    className="w-full border border-gray-300 dark:border-navy-600 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Workspace Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full border border-gray-300 dark:border-navy-600 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 transition-colors"
                  >
                    <option value="member">Member (Can edit & search)</option>
                    <option value="viewer">Viewer (Can search only)</option>
                    <option value="admin">Admin (Can manage settings)</option>
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={inviteLoading}
                  className="w-full bg-navy-900 hover:bg-navy-800 dark:bg-amber-400 dark:hover:bg-amber-500 dark:text-navy-900 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {inviteLoading ? 'Sending...' : 'Send Invitation'}
                </button>
              </form>
            </div>
          )}

          {/* Members List */}
          <div className="lg:col-span-2 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-gray-200 dark:border-navy-700">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Active Members</h2>
            </div>

            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-navy-900 dark:border-amber-400 border-t-transparent" />
              </div>
            ) : members.length === 0 ? (
              <div className="p-12 text-center text-gray-400 dark:text-gray-500">No members found.</div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-navy-700">
                {members.map((member) => (
                  <div key={member.user_id} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-gray-50 dark:hover:bg-navy-700/40 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-navy-700 text-navy-900 dark:text-white flex items-center justify-center font-bold text-lg">
                        {(member.username || 'U')[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-navy-900 dark:text-white">{member.username}</h4>
                          {!member.is_active && (
                            <span className="text-[10px] bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold">
                              <Clock size={10} /> Pending
                            </span>
                          )}
                        </div>
                        <p className="text-gray-500 dark:text-gray-400 text-sm">{member.email}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {isOrgOwner && member.role !== 'owner' ? (
                        <select
                          value={member.role}
                          onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                          className="border border-gray-300 dark:border-navy-600 bg-white dark:bg-navy-700 rounded-lg px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-navy-900 dark:focus:ring-amber-400"
                        >
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      ) : (
                        <span className="text-sm font-medium capitalize bg-gray-100 dark:bg-navy-700 border border-gray-200 dark:border-navy-600 px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-300">
                          {member.role}
                        </span>
                      )}

                      {isOrgAdmin && member.role !== 'owner' && member.user_id !== user.id && (
                        <button
                          onClick={() => handleRemove(member.user_id)}
                          className="text-gray-400 hover:text-red-500 p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                          title="Remove Member"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
      </div>
    </div>
  )
}
