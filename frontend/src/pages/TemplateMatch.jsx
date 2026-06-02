import { useState, useEffect } from 'react'
import { GitCompare, Loader2, CheckCircle, XCircle, AlertCircle, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { getDocuments, getTemplates, matchTemplate } from '../api'

const STATUS_ICONS = {
  present: { icon: CheckCircle, color: 'text-emerald-500' },
  missing_required: { icon: XCircle, color: 'text-red-500' },
  missing_optional: { icon: AlertCircle, color: 'text-amber-500' },
}

export default function TemplateMatch() {
  const [documents, setDocuments] = useState([])
  const [templates, setTemplates] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getDocuments(1, 100).then((d) => setDocuments(d.items || [])).catch(() => {})
    getTemplates().then(setTemplates).catch(() => {})
  }, [])

  const handleMatch = async () => {
    if (!selectedDoc || !selectedTemplate) {
      toast.error('Select both a document and a template')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const data = await matchTemplate(selectedDoc, parseInt(selectedTemplate))
      setResult(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Matching failed')
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-emerald-500'
    if (score >= 50) return 'text-amber-500'
    return 'text-red-500'
  }

  const getScoreRing = (score) => {
    if (score >= 80) return 'from-emerald-500 to-teal-500'
    if (score >= 50) return 'from-amber-500 to-orange-500'
    return 'from-red-500 to-rose-500'
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <GitCompare size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Template Matching</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">Compare your contract against standard templates</p>
            </div>
          </div>

          {/* Controls */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6 mb-6 shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Document</label>
                <select
                  value={selectedDoc}
                  onChange={(e) => setSelectedDoc(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="">Select document...</option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.filename}>{d.filename}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Template</label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="">Select template...</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name} ({t.template_type})</option>
                  ))}
                </select>
              </div>
            </div>
            <button
              onClick={handleMatch}
              disabled={!selectedDoc || !selectedTemplate || loading}
              className="w-full px-4 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg font-medium hover:from-cyan-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <><Loader2 size={18} className="animate-spin" /> Analyzing...</>
              ) : (
                <><Sparkles size={18} /> Run Compliance Check</>
              )}
            </button>
          </div>

          {/* Results */}
          {result && (
            <div className="space-y-6 animate-fade-in">
              {/* Score card */}
              <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6 shadow-sm text-center">
                <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br ${getScoreRing(result.compliance_score)} p-1`}>
                  <div className="w-full h-full rounded-full bg-white dark:bg-navy-800 flex items-center justify-center">
                    <span className={`text-3xl font-bold ${getScoreColor(result.compliance_score)}`}>
                      {result.compliance_score}%
                    </span>
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-3">Compliance Score</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {result.found_clauses}/{result.total_clauses} clauses found · {result.required_found}/{result.required_total} required clauses present
                </p>
              </div>

              {/* Clause breakdown */}
              <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200 dark:border-navy-700">
                  <h3 className="font-semibold text-gray-900 dark:text-white">Clause Analysis</h3>
                </div>
                <div className="divide-y divide-gray-100 dark:divide-navy-700">
                  {result.clause_results.map((cr, i) => {
                    const cfg = STATUS_ICONS[cr.status] || STATUS_ICONS.missing_optional
                    const Icon = cfg.icon
                    return (
                      <div key={i} className="px-6 py-4 flex items-start gap-3">
                        <Icon size={20} className={`${cfg.color} flex-shrink-0 mt-0.5`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                              {cr.clause_type.replace('-', ' ')}
                            </span>
                            {cr.required && (
                              <span className="text-xs px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded">Required</span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cr.description}</p>
                          {cr.summary && (
                            <p className="text-sm text-gray-700 dark:text-gray-300 mt-2 bg-gray-50 dark:bg-navy-700/50 rounded-lg p-2.5">
                              {cr.summary}
                            </p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
