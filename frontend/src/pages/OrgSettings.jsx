import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  getOrg, updateOrgSettings, uploadBrandingLogo,
  getWebhooks, createWebhook, deleteWebhook, testWebhook,
  configureSSO, runRetention
} from '../api'
import Navbar from '../components/Navbar'
import {
  Settings, Sparkles, Sliders, Webhook, ShieldAlert,
  Save, Palette, Image, Globe, CheckCircle, Trash2, Send, Cpu
} from 'lucide-react'

export default function OrgSettings() {
  const { isOrgAdmin } = useAuth()
  const [activeTab, setActiveTab] = useState('branding')
  
  // Organization settings states
  const [orgData, setOrgData] = useState(null)
  const [orgLoading, setOrgLoading] = useState(true)
  const [orgSettingsError, setOrgSettingsError] = useState(null)
  const [orgSettingsMessage, setOrgSettingsMessage] = useState(null)

  // Settings fields
  const [name, setName] = useState('')
  const [customSystemPrompt, setCustomSystemPrompt] = useState('')
  const [primaryColor, setPrimaryColor] = useState('#0f172a')
  const [secondaryColor, setSecondaryColor] = useState('#3b82f6')
  const [customDomain, setCustomDomain] = useState('')
  const [dataRetentionDays, setDataRetentionDays] = useState(0)

  // Logo file upload state
  const [logoFile, setLogoFile] = useState(null)
  const [logoUploading, setLogoUploading] = useState(false)

  // Webhooks states
  const [webhooks, setWebhooks] = useState([])
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookEvents, setWebhookEvents] = useState(['*'])
  const [webhookSecret, setWebhookSecret] = useState('')
  const [webhooksLoading, setWebhooksLoading] = useState(false)

  // SSO states
  const [ssoProvider, setSsoProvider] = useState('okta')
  const [ssoMetadataUrl, setSsoMetadataUrl] = useState('')
  const [ssoEntityId, setSsoEntityId] = useState('')

  const fetchOrgData = async () => {
    try {
      setOrgLoading(true)
      const data = await getOrg()
      setOrgData(data)
      setName(data.name || '')
      setCustomSystemPrompt(data.custom_system_prompt || '')
      setPrimaryColor(data.primary_color || '#0f172a')
      setSecondaryColor(data.secondary_color || '#3b82f6')
      setCustomDomain(data.custom_domain || '')
      setDataRetentionDays(data.data_retention_days || 0)
      setSsoProvider(data.sso_provider || 'okta')
      setSsoMetadataUrl(data.sso_metadata_url || '')
      setSsoEntityId(data.sso_entity_id || '')
    } catch (err) {
      setOrgSettingsError('Failed to load organization settings.')
    } finally {
      setOrgLoading(false)
    }
  }

  const fetchWebhooks = async () => {
    try {
      setWebhooksLoading(true)
      const data = await getWebhooks()
      setWebhooks(data)
    } catch (err) {
      console.error('Failed to load webhooks', err)
    } finally {
      setWebhooksLoading(false)
    }
  }

  useEffect(() => {
    fetchOrgData()
  }, [])

  useEffect(() => {
    if (activeTab === 'webhooks') {
      fetchWebhooks()
    }
  }, [activeTab])

  const handleUpdateSettings = async (e) => {
    e.preventDefault()
    try {
      setOrgSettingsMessage(null)
      setOrgSettingsError(null)
      await updateOrgSettings({
        name,
        custom_system_prompt: customSystemPrompt || null,
        primary_color: primaryColor,
        secondary_color: secondaryColor,
        custom_domain: customDomain || null,
        data_retention_days: parseInt(dataRetentionDays)
      })
      setOrgSettingsMessage('Workspace settings successfully updated.')
      fetchOrgData()
    } catch (err) {
      setOrgSettingsError(err.response?.data?.detail || 'Failed to update settings.')
    }
  }

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    try {
      setLogoUploading(true)
      setOrgSettingsMessage(null)
      setOrgSettingsError(null)
      const data = await uploadBrandingLogo(file)
      setOrgSettingsMessage('Workspace branding logo uploaded successfully!')
      fetchOrgData()
    } catch (err) {
      setOrgSettingsError('Failed to upload branding logo.')
    } finally {
      setLogoUploading(false)
    }
  }

  const handleCreateWebhook = async (e) => {
    e.preventDefault()
    if (!webhookUrl) return
    try {
      setOrgSettingsError(null)
      setOrgSettingsMessage(null)
      await createWebhook(webhookUrl, webhookEvents, webhookSecret || null)
      setOrgSettingsMessage('Webhook endpoint successfully registered.')
      setWebhookUrl('')
      setWebhookSecret('')
      fetchWebhooks()
    } catch (err) {
      setOrgSettingsError('Failed to register webhook.')
    }
  }

  const handleDeleteWebhook = async (id) => {
    if (!window.confirm('Are you sure you want to delete this webhook?')) return
    try {
      setOrgSettingsError(null)
      await deleteWebhook(id)
      fetchWebhooks()
    } catch (err) {
      setOrgSettingsError('Failed to delete webhook.')
    }
  }

  const handleTestWebhook = async (id) => {
    try {
      setOrgSettingsMessage(null)
      const res = await testWebhook(id)
      if (res.success) {
        setOrgSettingsMessage('Webhook test payload dispatched and delivered successfully! (Status 2xx)')
      } else {
        setOrgSettingsError('Webhook delivery failed or target returned non-2xx status.')
      }
    } catch (err) {
      setOrgSettingsError('Webhook test dispatch failed.')
    }
  }

  const handleConfigureSSO = async (e) => {
    e.preventDefault()
    try {
      setOrgSettingsMessage(null)
      setOrgSettingsError(null)
      await configureSSO(ssoProvider, ssoMetadataUrl, ssoEntityId)
      setOrgSettingsMessage('SSO successfully configured and enabled.')
      fetchOrgData()
    } catch (err) {
      setOrgSettingsError('Failed to configure SSO.')
    }
  }

  const handleManualRetention = async () => {
    if (!window.confirm('Are you sure you want to apply the retention cleanup manually? This will permanently delete records older than the configured days.')) return
    try {
      setOrgSettingsMessage(null)
      setOrgSettingsError(null)
      const res = await runRetention()
      setOrgSettingsMessage(`Manual retention run complete. Cleaned up: ${res.deleted_counts?.messages_deleted || 0} messages, ${res.deleted_counts?.ltm_deleted || 0} memory items.`)
    } catch (err) {
      setOrgSettingsError('Failed to trigger retention policy cleanup.')
    }
  }

  if (!isOrgAdmin) {
    return (
      <div className="flex min-h-screen bg-slate-900 text-slate-100">
        <Navbar />
        <main className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto flex items-center justify-center">
          <div className="text-center">
            <ShieldAlert className="text-rose-500 h-16 w-16 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
            <p className="text-slate-400">Only workspace administrators can manage organization settings.</p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      <Navbar />

      <main className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <Settings className="text-blue-500 h-8 w-8" />
            Workspace Settings
          </h1>
          <p className="text-slate-400 mt-1">Configure your firm branding, data retention, SAML SSO, and webhooks.</p>
        </div>

        {/* Notifications */}
        {orgSettingsMessage && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-3">
            <CheckCircle size={20} />
            <span>{orgSettingsMessage}</span>
          </div>
        )}
        {orgSettingsError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-3">
            <ShieldAlert size={20} />
            <span>{orgSettingsError}</span>
          </div>
        )}

        {/* Tabs Bar */}
        <div className="flex border-b border-slate-700/50 mb-8 overflow-x-auto">
          {[
            { id: 'branding', label: 'White-Label Branding', icon: Palette },
            { id: 'retention', label: 'Data Retention', icon: Sliders },
            { id: 'sso', label: 'SSO/SAML', icon: Globe },
            { id: 'webhooks', label: 'Webhooks', icon: Webhook }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 text-sm font-semibold transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-500'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {orgLoading ? (
          <div className="p-12 flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
          </div>
        ) : (
          <div className="bg-slate-800/30 border border-slate-700/50 p-8 rounded-2xl backdrop-blur-xl">
            {/* Branding Tab */}
            {activeTab === 'branding' && (
              <div className="space-y-6">
                <form onSubmit={handleUpdateSettings} className="space-y-6">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                    <Palette className="text-blue-500" size={20} /> Branding Config
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Firm Workspace Name</label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Custom Domain</label>
                      <input
                        type="text"
                        value={customDomain}
                        onChange={(e) => setCustomDomain(e.target.value)}
                        placeholder="e.g. lex.myfirm.com"
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Primary Branding Color</label>
                      <div className="flex gap-3">
                        <input
                          type="color"
                          value={primaryColor}
                          onChange={(e) => setPrimaryColor(e.target.value)}
                          className="h-12 w-16 bg-transparent border-0 cursor-pointer"
                        />
                        <input
                          type="text"
                          value={primaryColor}
                          onChange={(e) => setPrimaryColor(e.target.value)}
                          className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 font-mono"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Secondary Accent Color</label>
                      <div className="flex gap-3">
                        <input
                          type="color"
                          value={secondaryColor}
                          onChange={(e) => setSecondaryColor(e.target.value)}
                          className="h-12 w-16 bg-transparent border-0 cursor-pointer"
                        />
                        <input
                          type="text"
                          value={secondaryColor}
                          onChange={(e) => setSecondaryColor(e.target.value)}
                          className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">Custom Legal System Prompt</label>
                    <textarea
                      rows={5}
                      value={customSystemPrompt}
                      onChange={(e) => setCustomSystemPrompt(e.target.value)}
                      placeholder="e.g. Prepend specific firm rules or policies to RAG search answers..."
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono text-sm"
                    />
                  </div>

                  <button
                    type="submit"
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-all"
                  >
                    <Save size={18} /> Save Settings
                  </button>
                </form>

                <div className="pt-6 border-t border-slate-700/50 space-y-4">
                  <h4 className="text-md font-bold text-white flex items-center gap-2">
                    <Image className="text-blue-500" size={18} /> Branding Logo
                  </h4>
                  <div className="flex items-center gap-6">
                    <div className="w-16 h-16 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center overflow-hidden">
                      {orgData?.logo_url ? (
                        <img src={orgData.logo_url} alt="Logo" className="w-full h-full object-contain bg-white p-1" />
                      ) : (
                        <Image size={24} className="text-slate-600" />
                      )}
                    </div>
                    <div>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleLogoUpload}
                        className="hidden"
                        id="logo-upload-input"
                      />
                      <label
                        htmlFor="logo-upload-input"
                        className="bg-slate-700 hover:bg-slate-600 text-white text-sm font-semibold px-4 py-2 rounded-lg cursor-pointer transition-all block"
                      >
                        {logoUploading ? 'Uploading Logo...' : 'Upload Workspace Logo'}
                      </label>
                      <p className="text-xs text-slate-500 mt-1.5">Recommended size: 120x120px PNG or JPG.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Retention Tab */}
            {activeTab === 'retention' && (
              <div className="space-y-6">
                <form onSubmit={handleUpdateSettings} className="space-y-6">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                    <Sliders className="text-blue-500" size={20} /> Data Retention Policy
                  </h3>

                  <div className="max-w-xl">
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">Auto-Deletion Period</label>
                    <select
                      value={dataRetentionDays}
                      onChange={(e) => setDataRetentionDays(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    >
                      <option value="0">Keep Forever (Default)</option>
                      <option value="30">30 Days</option>
                      <option value="60">60 Days</option>
                      <option value="90">90 Days</option>
                      <option value="180">180 Days</option>
                      <option value="365">365 Days</option>
                    </select>
                    <p className="text-xs text-slate-500 mt-2">
                      When enabled, chat messages, session summaries, analytics, and audit logs older than the selected period will be deleted permanently. Documents require manual deletion.
                    </p>
                  </div>

                  <button
                    type="submit"
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-all"
                  >
                    <Save size={18} /> Save Retention Policy
                  </button>
                </form>

                <div className="pt-6 border-t border-slate-700/50 space-y-4">
                  <h4 className="text-md font-bold text-white">Manual Force Clean</h4>
                  <p className="text-sm text-slate-400">Trigger the auto-retention prune immediately rather than waiting for the automated nightly schedule.</p>
                  <button
                    onClick={handleManualRetention}
                    className="bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2"
                  >
                    <Trash2 size={16} /> Run Retention Cleanup Now
                  </button>
                </div>
              </div>
            )}

            {/* SSO Tab */}
            {activeTab === 'sso' && (
              <form onSubmit={handleConfigureSSO} className="space-y-6">
                <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                  <Globe className="text-blue-500" size={20} /> SAML 2.0 Single Sign-On (SSO)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">SSO Identity Provider</label>
                    <select
                      value={ssoProvider}
                      onChange={(e) => setSsoProvider(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    >
                      <option value="okta">Okta</option>
                      <option value="azure">Azure AD (Entra ID)</option>
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-slate-400 mb-1.5">SAML IdP Metadata URL</label>
                    <input
                      type="url"
                      value={ssoMetadataUrl}
                      onChange={(e) => setSsoMetadataUrl(e.target.value)}
                      required
                      placeholder="https://example.okta.com/app/exk.../sso/saml/metadata"
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1.5">SAML Entity ID</label>
                  <input
                    type="text"
                    value={ssoEntityId}
                    onChange={(e) => setSsoEntityId(e.target.value)}
                    required
                    placeholder="urn:amazon:cognito:sp:..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  />
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-500 space-y-2">
                  <p className="font-bold text-slate-400">Configure these fields in your Identity Provider (IdP):</p>
                  <p>• Assertion Consumer Service (ACS) URL: <span className="text-blue-400 font-mono">https://lexbot.ai/api/auth/sso/{orgData?.slug}/callback</span></p>
                  <p>• Service Provider Entity ID: <span className="text-blue-400 font-mono">https://lexbot.ai/api/auth/sso/{orgData?.slug}/metadata</span></p>
                </div>

                <button
                  type="submit"
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-all"
                >
                  <Save size={18} /> Enable Single Sign-On
                </button>
              </form>
            )}

            {/* Webhooks Tab */}
            {activeTab === 'webhooks' && (
              <div className="space-y-6">
                <form onSubmit={handleCreateWebhook} className="space-y-6">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
                    <Webhook className="text-blue-500" size={20} /> Register Webhook
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Payload Endpoint URL</label>
                      <input
                        type="url"
                        value={webhookUrl}
                        onChange={(e) => setWebhookUrl(e.target.value)}
                        required
                        placeholder="https://api.yourfirm.com/lexbot-handler"
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1.5">Signing Secret (HMAC-SHA256)</label>
                      <input
                        type="text"
                        value={webhookSecret}
                        onChange={(e) => setWebhookSecret(e.target.value)}
                        placeholder="Leave empty for auto-generated secret"
                        className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-all"
                  >
                    <Webhook size={18} /> Register Endpoint
                  </button>
                </form>

                <div className="pt-6 border-t border-slate-700/50 space-y-4">
                  <h4 className="text-md font-bold text-white mb-2">Registered Webhooks</h4>
                  
                  {webhooksLoading ? (
                    <div className="flex justify-center p-6">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-500 border-t-transparent" />
                    </div>
                  ) : webhooks.length === 0 ? (
                    <p className="text-slate-500 text-sm">No webhook endpoints registered yet.</p>
                  ) : (
                    <div className="divide-y divide-slate-700/50 border border-slate-700/50 rounded-xl overflow-hidden bg-slate-900/30">
                      {webhooks.map((ep) => (
                        <div key={ep.id} className="p-4 flex items-center justify-between gap-4 hover:bg-slate-800/20 transition-all">
                          <div className="min-w-0">
                            <h5 className="font-bold text-white truncate text-sm">{ep.url}</h5>
                            <p className="text-xs text-slate-500 mt-1 font-mono">
                              Events: {ep.events.join(', ')}
                            </p>
                            {ep.last_triggered_at && (
                              <p className="text-[10px] text-slate-500 mt-0.5">
                                Last active: {new Date(ep.last_triggered_at).toLocaleString()} | Failures: {ep.failure_count}
                              </p>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleTestWebhook(ep.id)}
                              className="text-slate-400 hover:text-emerald-400 p-2 hover:bg-slate-700/30 rounded-lg transition-all"
                              title="Test delivery"
                            >
                              <Send size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteWebhook(ep.id)}
                              className="text-slate-400 hover:text-red-400 p-2 hover:bg-slate-700/30 rounded-lg transition-all"
                              title="Delete webhook"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
