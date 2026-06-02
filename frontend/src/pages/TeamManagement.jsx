import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getMembers, inviteMember, removeMember, updateMemberRole, leaveOrg } from '../api'
import Navbar from '../components/Navbar'
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
      setError(err.response?.data?.detail || 'Failed to send invitation.')
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
      setError(err.response?.data?.detail || 'Failed to change role.')
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
      setError(err.response?.data?.detail || 'Failed to remove member.')
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
      setError(err.response?.data?.detail || 'Failed to leave organization.')
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      <Navbar />

      <main className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <Users className="text-blue-500 h-8 w-8" />
              Team Management
            </h1>
            <p className="text-slate-400 mt-1">Manage firm workspaces, invite colleagues, and control roles.</p>
          </div>
          {!isOrgOwner && (
            <button
              onClick={handleLeave}
              className="flex items-center gap-2 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white px-4 py-2 rounded-lg border border-red-500/30 transition-all font-semibold"
            >
              <LogOut size={16} />
              Leave Workspace
            </button>
          )}
        </div>

        {/* Notifications */}
        {message && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-3 animate-fade-in">
            <CheckCircle size={20} />
            <span>{message}</span>
          </div>
        )}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-3 animate-fade-in">
            <ShieldAlert size={20} />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Invite Box */}
          {isOrgAdmin && (
            <div className="lg:col-span-1 bg-slate-800/50 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl h-fit">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <UserPlus className="text-blue-500" size={20} />
                Invite Colleague
              </h2>
              <form onSubmit={handleInvite} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1.5">Email Address</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                    placeholder="colleague@firm.com"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1.5">Workspace Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  >
                    <option value="member">Member (Can edit & search)</option>
                    <option value="viewer">Viewer (Can search only)</option>
                    <option value="admin">Admin (Can manage settings)</option>
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={inviteLoading}
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {inviteLoading ? 'Sending...' : 'Send Invitation'}
                </button>
              </form>
            </div>
          )}

          {/* Members List */}
          <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-xl">
            <div className="p-6 border-b border-slate-700/50">
              <h2 className="text-xl font-bold text-white">Active Members</h2>
            </div>
            
            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
              </div>
            ) : members.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No members found.</div>
            ) : (
              <div className="divide-y divide-slate-700/50">
                {members.map((member) => (
                  <div key={member.user_id} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/20 transition-all">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center font-bold text-lg">
                        {(member.username || 'U')[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-white">{member.username}</h4>
                          {!member.is_active && (
                            <span className="text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold">
                              <Clock size={10} /> Pending
                            </span>
                          )}
                        </div>
                        <p className="text-slate-400 text-sm">{member.email}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {isOrgOwner && member.role !== 'owner' ? (
                        <select
                          value={member.role}
                          onChange={(e) => handleRoleChange(member.user_id, e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      ) : (
                        <span className="text-sm font-semibold capitalize bg-slate-700/30 border border-slate-600/30 px-3 py-1.5 rounded-lg text-slate-300">
                          {member.role}
                        </span>
                      )}

                      {isOrgAdmin && member.role !== 'owner' && member.user_id !== user.id && (
                        <button
                          onClick={() => handleRemove(member.user_id)}
                          className="text-slate-400 hover:text-red-400 p-2 hover:bg-slate-700/50 rounded-lg transition-all"
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
  )
}
