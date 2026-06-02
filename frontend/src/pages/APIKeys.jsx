import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { getAPIKeys, createAPIKey, deleteAPIKey } from '../api'
import Navbar from '../components/Navbar'
import { Key, Plus, Trash2, Copy, Check, Eye, EyeOff, Calendar, AlertTriangle } from 'lucide-react'

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
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      <Navbar />

      <main className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <Key className="text-blue-500 h-8 w-8" />
            API Key Management
          </h1>
          <p className="text-slate-400 mt-1">Authenticate programmatic requests and integrate LexBot into your legal tech stack.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
            {error}
          </div>
        )}

        {/* Secret Key Modal/Alert (Show once on create) */}
        {newKeyData && (
          <div className="mb-8 p-6 rounded-2xl bg-amber-500/10 border-2 border-amber-500/30 text-slate-100 animate-pulse-subtle">
            <div className="flex items-start gap-4">
              <AlertTriangle className="text-amber-500 h-6 w-6 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-bold text-white mb-2">Copy your Secret API Key</h3>
                <p className="text-slate-300 text-sm mb-4">
                  For security reasons, we can only display this key once. If you lose it, you will have to revoke it and generate a new one.
                </p>
                <div className="flex gap-2 max-w-xl">
                  <input
                    type="text"
                    readOnly
                    value={newKeyData.key}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 font-mono text-amber-400 focus:outline-none focus:ring-0"
                  />
                  <button
                    onClick={handleCopy}
                    className="bg-amber-500 hover:bg-amber-400 text-navy-950 font-bold px-4 py-3 rounded-xl flex items-center justify-center gap-2 transition-all"
                  >
                    {copied ? <Check size={18} /> : <Copy size={18} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <button
                  onClick={() => setNewKeyData(null)}
                  className="mt-4 text-xs font-semibold text-slate-400 hover:text-white transition-all underline"
                >
                  I have copied my key, close this panel
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Create Form */}
          {isOrgAdmin && (
            <div className="lg:col-span-1 bg-slate-800/50 border border-slate-700/50 p-6 rounded-2xl backdrop-blur-xl h-fit">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Plus className="text-blue-500" size={20} />
                Generate New Key
              </h2>
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1.5">Key Name / Description</label>
                  <input
                    type="text"
                    value={keyName}
                    onChange={(e) => setKeyName(e.target.value)}
                    required
                    placeholder="e.g. DocuSign Integration"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1.5">Expiration Period</label>
                  <select
                    value={expiresIn}
                    onChange={(e) => setExpiresIn(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  >
                    <option value="30">30 Days</option>
                    <option value="90">90 Days</option>
                    <option value="365">365 Days</option>
                    <option value="">Never Expire</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2"
                >
                  Generate API Key
                </button>
              </form>
            </div>
          )}

          {/* Keys List */}
          <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-xl">
            <div className="p-6 border-b border-slate-700/50">
              <h2 className="text-xl font-bold text-white">Active Keys</h2>
            </div>
            
            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
              </div>
            ) : keys.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No active API keys found. Generate one to get started.</div>
            ) : (
              <div className="divide-y divide-slate-700/50">
                {keys.map((k) => (
                  <div key={k.id} className="p-6 flex items-center justify-between gap-4 hover:bg-slate-800/20 transition-all">
                    <div className="flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center">
                        <Key size={18} />
                      </div>
                      <div>
                        <h4 className="font-bold text-white">{k.name}</h4>
                        <p className="text-slate-400 text-sm font-mono mt-0.5">
                          {k.prefix}••••••••••••••••
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
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
                            <span className="text-emerald-400 font-semibold">Never Expires</span>
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
                        className="text-slate-400 hover:text-red-400 p-2 hover:bg-slate-700/50 rounded-lg transition-all"
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
  )
}
