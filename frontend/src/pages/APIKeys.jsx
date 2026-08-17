import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getAPIKeys, createAPIKey, deleteAPIKey } from '../api'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import { Key, Plus, Trash2, Copy, Check, Calendar, AlertTriangle } from 'lucide-react'

export default function APIKeys() {
  const { isOrgAdmin } = useAuth()
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [keyName, setKeyName] = useState('')
  const [expiresIn, setExpiresIn] = useState('30')
  const [newKeyData, setNewKeyData] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  const fetchKeys = async () => {
    try {
      setLoading(true)
      const data = await getAPIKeys()
      setKeys(data)
    } catch (err) {
      setError('Failed to fetch API keys.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKeys()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!keyName) return
    try {
      setError(null)
      const data = await createAPIKey(keyName, expiresIn ? parseInt(expiresIn) : null)
      setNewKeyData(data)
      setKeyName('')
      fetchKeys()
    } catch (err) {
      setError('Failed to create API key.')
    }
  }

  const handleDelete = async (keyId) => {
    if (!window.confirm('Are you sure you want to revoke this API key? Systems using this key will immediately lose access.')) return
    try {
      setError(null)
      await deleteAPIKey(keyId)
      fetchKeys()
    } catch (err) {
      setError('Failed to revoke API key.')
    }
  }

  const handleCopy = () => {
    if (!newKeyData?.key) return
    navigator.clipboard.writeText(newKeyData.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

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
              <Key className="text-navy-900 h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-navy-900 dark:text-white">
              API Key Management
            </h1>
          </div>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Authenticate programmatic requests and integrate LexBot into your legal tech stack.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Secret Key Modal/Alert (Show once on create) */}
        {newKeyData && (
          <div className="mb-8 p-6 rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-navy-900 dark:text-gray-100">
            <div className="flex items-start gap-4">
              <AlertTriangle className="text-amber-600 dark:text-amber-400 h-6 w-6 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-bold text-amber-800 dark:text-amber-300 mb-2">Copy your Secret API Key</h3>
                <p className="text-amber-700 dark:text-amber-400 text-sm mb-4">
                  For security reasons, we can only display this key once. If you lose it, you will have to revoke it and generate a new one.
                </p>
                <div className="flex gap-2 max-w-xl">
                  <input
                    type="text"
                    readOnly
                    value={newKeyData.key}
                    className="w-full bg-white dark:bg-navy-900 border border-gray-300 dark:border-navy-600 rounded-lg px-3 py-2.5 font-mono text-sm text-amber-700 dark:text-amber-400 focus:outline-none focus:ring-0"
                  />
                  <button
                    onClick={handleCopy}
                    className="bg-navy-900 hover:bg-navy-800 dark:bg-amber-400 dark:hover:bg-amber-500 dark:text-navy-900 text-white font-medium px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <button
                  onClick={() => setNewKeyData(null)}
                  className="mt-4 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-white transition-colors underline"
                >
                  I have copied my key, close this panel
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Create Form */}
          {isOrgAdmin && (
            <div className="lg:col-span-1 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 p-6 rounded-xl shadow-sm h-fit">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white mb-4 flex items-center gap-2">
                <Plus className="text-amber-600 dark:text-amber-400" size={18} />
                Generate New Key
              </h2>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Key Name / Description</label>
                  <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    required
                    placeholder="e.g. DocuSign Integration"
                    className="w-full border border-gray-300 dark:border-navy-600 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Expiration Period</label>
                  <select
                    value={expiresIn}
                    onChange={(e) => setExpiresIn(e.target.value)}
                    className="w-full border border-gray-300 dark:border-navy-600 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 transition-colors"
                  >
                    <option value="30">30 Days</option>
                    <option value="90">90 Days</option>
                    <option value="365">365 Days</option>
                    <option value="">Never Expire</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="w-full bg-navy-900 hover:bg-navy-800 dark:bg-amber-400 dark:hover:bg-amber-500 dark:text-navy-900 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  Generate API Key
                </button>
              </form>
            </div>
          )}

          {/* Keys List */}
          <div className="lg:col-span-2 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-gray-200 dark:border-navy-700">
              <h2 className="text-lg font-semibold text-navy-900 dark:text-white">Active Keys</h2>
            </div>

            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-navy-900 dark:border-amber-400 border-t-transparent" />
              </div>
            ) : keys.length === 0 ? (
              <div className="p-12 text-center text-gray-400 dark:text-gray-500">No active API keys found. Generate one to get started.</div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-navy-700">
                {keys.map((k) => (
                  <div key={k.id} className="p-6 flex items-center justify-between gap-4 hover:bg-gray-50 dark:hover:bg-navy-700/40 transition-colors">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400 flex items-center justify-center">
                        <Key size={18} />
                      </div>
                      <div>
                        <h4 className="font-semibold text-navy-900 dark:text-white">{k.name}</h4>
                        <p className="text-gray-500 dark:text-gray-400 text-sm font-mono mt-0.5">
                          {k.prefix}••••••••••••••••
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                          <span className="flex items-center gap-1">
                            <Calendar size={12} />
                            Created: {new Date(k.created_at).toLocaleDateString()}
                          </span>
                          {k.expires_at ? (
                            <span className="flex items-center gap-1">
                              <Calendar size={12} />
                              Expires: {new Date(k.expires_at).toLocaleDateString()}
                            </span>
                          ) : (
                            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Never Expires</span>
                          )}
                          {k.last_used_at && (
                            <span>Last used: {new Date(k.last_used_at).toLocaleDateString()}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {isOrgAdmin && (
                      <button
                        onClick={() => handleDelete(k.id)}
                        className="text-gray-400 hover:text-red-500 p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Revoke API Key"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
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
