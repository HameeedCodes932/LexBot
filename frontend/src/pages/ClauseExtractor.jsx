import { useState, useEffect } from 'react'
import { Search, ChevronDown, ChevronUp, Download, Bookmark } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { getDocuments, extractClauses, saveClause } from '../api'

const CLAUSE_TYPES = [
  'indemnification', 'termination', 'payment', 'liability',
  'confidentiality', 'governing-law', 'dispute-resolution',
  'warranty', 'intellectual-property', 'force-majeure',
]

export default function ClauseExtractor() {
  const [docs, setDocs] = useState([])
  const [documentName, setDocumentName] = useState('')
  const [clauseType, setClauseType] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')
  const [openRaw, setOpenRaw] = useState(null)
  const [savingIndex, setSavingIndex] = useState(null)
  const [savedIndices, setSavedIndices] = useState([])

  const handleSaveToLibrary = async (r, idx) => {
    setSavingIndex(idx)
    try {
      await saveClause(
        results.clause_type,
        r.raw_text,
        `${results.clause_type.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} - ${results.document_name}`,
        results.document_name,
        r.summary
      )
      setSavedIndices(prev => [...prev, idx])
      toast.success('Clause saved to library')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save clause')
    } finally {
      setSavingIndex(null)
    }
  }

  useEffect(() => {
    getDocuments().then((data) => {
      if (Array.isArray(data)) {
        setDocs(data)
      } else if (data?.documents) {
        setDocs(data.documents)
      } else if (data?.items) {
        setDocs(data.items)
      } else {
        setDocs([])
      }
    }).catch(() => {})
  }, [])

  const handleExtract = async () => {
    if (!documentName || !clauseType) return
    setError(''); setResults(null); setSavedIndices([]); setLoading(true)
    try {
      const data = await extractClauses(documentName, clauseType)
      setResults(data)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : detail?.message || 'Extraction failed.')
    } finally { setLoading(false) }
  }

  const exportResults = () => {
    if (!results?.results?.length) { toast.error('No results to export'); return }
    const text = results.results
      .map((r, i) => `Result ${i + 1} (Chunk ${r.chunk_index}):\n${r.summary}\n`)
      .join('\n---\n\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `clauses-${clauseType}.txt`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Results exported')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="px-4 md:px-6 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white" data-tour="tools">Clause Extractor</h2>
        </div>

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6">
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 mb-6 flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Document</label>
              <select value={documentName} onChange={(e) => setDocumentName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors">
                <option value="">Select a document</option>
                {docs.map((d) => <option key={d.id} value={d.filename}>{d.filename}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Clause Type</label>
              <select value={clauseType} onChange={(e) => setClauseType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors">
                <option value="">Select clause type</option>
                {CLAUSE_TYPES.map((ct) => <option key={ct} value={ct}>{ct}</option>)}
              </select>
            </div>
            <button onClick={handleExtract} disabled={!documentName || !clauseType || loading}
              className="px-5 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2">
              {loading ? <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Extracting...</>
                : <><Search size={16} /> Extract</>}
            </button>
          </div>

          {error && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg text-sm text-red-600 dark:text-red-400">{error}</div>}

          {results && (
            <div>
              {results.message && !results.total_clauses_found ? (
                <div className="text-center py-12 text-gray-400 dark:text-gray-500">
                  <Search size={40} className="mx-auto mb-3 opacity-50" />
                  <p className="text-sm">{results.message}</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Found <span className="font-semibold text-navy-900 dark:text-amber-400">{results.total_clauses_found}</span> clause(s)
                    </p>
                    <button onClick={exportResults}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 bg-gray-100 dark:bg-navy-700 rounded-lg hover:bg-gray-200 dark:hover:bg-navy-600 transition-colors">
                      <Download size={14} /> Export
                    </button>
                  </div>
                  <div className="space-y-4">
                    {results.results?.map((r, i) => (
                      <div key={i} className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-xl p-4 animate-fade-in">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white">Chunk {r.chunk_index}</span>
                        </div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">{r.summary}</p>
                        <div className="flex items-center gap-4 mt-2">
                          <button onClick={() => setOpenRaw(openRaw === i ? null : i)}
                            className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 transition-colors">
                            {openRaw === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            {openRaw === i ? 'Hide raw text' : 'View raw text'}
                          </button>
                          <button
                            onClick={() => handleSaveToLibrary(r, i)}
                            disabled={savedIndices.includes(i) || savingIndex === i}
                            className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
                              savedIndices.includes(i)
                                ? 'text-emerald-600 dark:text-emerald-400 cursor-default'
                                : 'text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400'
                            }`}
                          >
                            <Bookmark size={14} className={savedIndices.includes(i) ? 'fill-current' : ''} />
                            {savedIndices.includes(i) ? 'Saved to Library' : savingIndex === i ? 'Saving...' : 'Save to Library'}
                          </button>
                        </div>
                        {openRaw === i && (
                          <pre className="mt-2 p-3 bg-gray-50 dark:bg-navy-900 rounded-lg text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">{r.raw_text}</pre>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {!results && !loading && !error && (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400 dark:text-gray-500">
              <Search size={48} className="mb-3 opacity-50" />
              <p className="text-sm">Select a document and clause type, then click Extract</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
