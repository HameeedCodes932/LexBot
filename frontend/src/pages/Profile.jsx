import { useState, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  User, Mail, Shield, Building2, Calendar, CreditCard,
  Trash2, BadgeCheck, Phone, Camera, Save, X, Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import DeleteDataModal from '../components/DeleteDataModal'
import { updateProfile, uploadAvatar } from '../api'

export default function Profile() {
  const { user, setUser } = useAuth()
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const [form, setForm] = useState({
    username: user?.username || '',
    email: user?.email || '',
    firm_name: user?.firm_name || '',
    phone_number: user?.phone_number || '',
  })

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updateProfile(form)
      setUser(updated)
      setEditing(false)
      toast.success('Profile updated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file')
      return
    }
    setUploading(true)
    try {
      const { avatar_url } = await uploadAvatar(file)
      const updated = await updateProfile({ avatar_url })
      setUser(updated)
      toast.success('Profile picture updated')
    } catch (err) {
      toast.error('Failed to upload avatar')
    } finally {
      setUploading(false)
    }
  }

  const avatarSrc = user?.avatar_url

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0">
        <WorkspaceTopBar />
        <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-2xl mx-auto px-4 py-8">
          {/* Profile header */}
          <div className="bg-white dark:bg-navy-800 rounded-2xl border border-gray-200 dark:border-navy-700 p-8 mb-6">
            <div className="flex items-center gap-6">
              <div className="relative shrink-0">
                <div className="w-20 h-20 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 font-bold text-2xl shadow-md overflow-hidden">
                  {avatarSrc ? (
                    <img src={avatarSrc} alt="avatar" className="w-full h-full object-cover" />
                  ) : (
                    (user?.username || 'U')[0].toUpperCase()
                  )}
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-amber-400 hover:bg-amber-500 text-navy-900 flex items-center justify-center shadow-md transition-colors disabled:opacity-50"
                >
                  {uploading ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleAvatarUpload}
                />
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-2xl font-bold text-navy-900 dark:text-white truncate">{user?.username}</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400 capitalize flex items-center gap-2 mt-1">
                  <BadgeCheck size={14} className="text-amber-500" />
                  {user?.role}
                  {user?.firm_name && (
                    <>
                      <span className="text-gray-300 dark:text-navy-600">&bull;</span>
                      <Building2 size={14} className="text-gray-400" />
                      {user.firm_name}
                    </>
                  )}
                </p>
              </div>
              <button
                onClick={() => editing ? setEditing(false) : setEditing(true)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  editing
                    ? 'bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-navy-600'
                    : 'bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white hover:bg-navy-800 dark:hover:bg-amber-500'
                }`}
              >
                {editing ? 'Cancel' : 'Edit'}
              </button>
            </div>
          </div>

          {/* Account Details */}
          <div className="bg-white dark:bg-navy-800 rounded-2xl border border-gray-200 dark:border-navy-700 p-6 mb-6">
            <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
              {editing ? 'Edit Details' : 'Account Details'}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InfoField
                label="Username"
                icon={User}
                value={form.username}
                editing={editing}
                onChange={(v) => setForm({ ...form, username: v })}
              />
              <InfoField
                label="Email"
                icon={Mail}
                value={form.email}
                editing={editing}
                onChange={(v) => setForm({ ...form, email: v })}
              />
              <InfoField
                label="Role"
                icon={Shield}
                value={user?.role}
                capitalize
              />
              <InfoField
                label="Firm"
                icon={Building2}
                value={form.firm_name}
                editing={editing}
                onChange={(v) => setForm({ ...form, firm_name: v })}
              />
              <InfoField
                label="Phone"
                icon={Phone}
                value={form.phone_number}
                editing={editing}
                onChange={(v) => setForm({ ...form, phone_number: v })}
              />
              <InfoField
                label="Joined"
                icon={Calendar}
                value={user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}
              />
              <InfoField
                label="Subscription"
                icon={CreditCard}
                value={user?.subscription_status || 'free'}
                capitalize
              />
            </div>
            {editing && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-xl text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 transition-colors"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Changes
              </button>
            )}
          </div>

          {/* Danger Zone */}
          <div className="bg-white dark:bg-navy-800 rounded-2xl border border-red-200 dark:border-red-900/50 p-6">
            <h2 className="text-sm font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider mb-1">Danger Zone</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Permanently delete your account and all associated data.</p>
            <button
              onClick={() => setDeleteModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm font-medium hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors border border-red-200 dark:border-red-900/50"
            >
              <Trash2 size={16} />
              Delete My Data
            </button>
          </div>
        </div>
      </div>

      <DeleteDataModal open={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} />
      </div>
    </div>
  )
}

function InfoField({ label, icon: Icon, value, editing, onChange, capitalize }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 dark:bg-navy-700/50 border border-gray-100 dark:border-navy-700">
      <div className="w-9 h-9 rounded-lg bg-navy-100 dark:bg-navy-600 flex items-center justify-center shrink-0">
        <Icon size={16} className="text-navy-600 dark:text-amber-400" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        {editing && onChange ? (
          <input
            type={label === 'Email' ? 'email' : label === 'Phone' ? 'tel' : 'text'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-transparent text-sm font-medium text-navy-900 dark:text-white border-b border-gray-300 dark:border-navy-500 focus:border-amber-500 dark:focus:border-amber-400 outline-none pb-0.5"
          />
        ) : (
          <p className={`text-sm font-medium text-navy-900 dark:text-white truncate ${capitalize ? 'capitalize' : ''}`}>
            {value || 'N/A'}
          </p>
        )}
      </div>
    </div>
  )
}
