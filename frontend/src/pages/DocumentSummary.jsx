import { useState, useEffect } from 'react'
import { FileBarChart, Loader2, FileText, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { getDocuments, summarizeDocument } from '../api'

const SUMMARY_TYPES = [
  { value: 'brief', label: 'Brief', desc: 'Concise 3-5 sentence overview' },
  { value: 'detailed', label: 'Detailed', desc: 'Full structured analysis' },
  { value: 'executive', label: 'Executive', desc: 'Senior partner briefing' },
]

export default function DocumentSummary() {
  const [documents, setDocuments] = useState([])
  const [selectedDoc, setSelectedDoc] = useState('')
  const [summaryType, setSummaryType] = useState('detailed')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getDocuments(1, 100)
      .then((d) => setDocuments(d.items || []))
      .catch(() => toast.error('Failed to load documents'))
  }, [])

  const handleSummarize = async () => {
    if (!selectedDoc) {
      toast.error('Please select a document')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const data = await summarizeDocument(selectedDoc, summaryType)
      setResult(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Summarization failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-8">
          {/* Header */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <FileBarChart size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Contract Summarization</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">AI-powered document summaries with key insights</p>
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
                  className="w-full px-3 py-2.5 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
                >
                  <option value="">Select a document...</option>
                  {documents.map((d) => (
                    <option key={d.id} value={d.filename}>{d.filename}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Summary Style</label>
                <div className="flex gap-2">
                  {SUMMARY_TYPES.map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setSummaryType(t.value)}
                      className={`flex-1 px-3 py-2.5 rounded-lg text-sm font-medium border transition-all ${
                        summaryType === t.value
                          ? 'bg-violet-50 dark:bg-violet-900/30 border-violet-300 dark:border-violet-700 text-violet-700 dark:text-violet-400'
                          : 'border-gray-200 dark:border-navy-600 text-gray-600 dark:text-gray-400 hover:border-violet-300 dark:hover:border-violet-700'
                      }`}
                      title={t.desc}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <button
              onClick={handleSummarize}
              disabled={!selectedDoc || loading}
              className="w-full px-4 py-3 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-lg font-medium hover:from-violet-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Analyzing document...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Generate Summary
                </>
              )}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm animate-fade-in">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-navy-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-violet-500" />
                  <h3 className="font-semibold text-gray-900 dark:text-white">{result.document_name}</h3>
                </div>
                <span className="text-xs text-gray-400 bg-gray-100 dark:bg-navy-700 px-2 py-1 rounded-full">
                  {result.chunks_analyzed}/{result.total_chunks} chunks analyzed
                </span>
              </div>
              <div className="px-6 py-5 prose prose-sm max-w-none dark:text-gray-200 dark:prose-headings:text-white prose-headings:text-gray-900">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {result.summary}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
