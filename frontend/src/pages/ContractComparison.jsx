import { useState, useEffect } from 'react'
import { Scale, AlertTriangle, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { getDocuments, compareClauses } from '../api'

const CLAUSE_TYPES = [
  'indemnification', 'termination', 'payment', 'liability',
  'confidentiality', 'governing-law', 'dispute-resolution',
  'warranty', 'intellectual-property', 'force-majeure',
]

export default function ContractComparison() {
  const [docs, setDocs] = useState([])
  const [docOne, setDocOne] = useState('')
  const [docTwo, setDocTwo] = useState('')
  const [clauseType, setClauseType] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getDocuments().then(setDocs).catch(() => {})
  }, [])

  const sameDoc = docOne && docTwo && docOne === docTwo
  const canCompare = docOne && docTwo && clauseType && !sameDoc

  const handleCompare = async () => {
    if (!canCompare) return
    setError(''); setResult(null); setLoading(true)
    try {
      const data = await compareClauses(docOne, docTwo, clauseType)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Comparison failed.')
    } finally { setLoading(false) }
  }

  const exportComparison = () => {
    if (!result?.comparison) { toast.error('No comparison to export'); return }
    const text = `Comparison: ${result.document_one} vs ${result.document_two}\nClause Type: ${result.clause_type}\n\n${result.comparison}`
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `comparison-${clauseType}.txt`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Comparison exported')
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="px-4 md:px-6 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white" data-tour="tools">Compare Contracts</h2>
        </div>

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6">
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 mb-6 grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Document One</label>
              <select value={docOne} onChange={(e) => setDocOne(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors">
                <option value="">Select document</option>
                {docs.map((d) => <option key={d.id} value={d.filename}>{d.filename}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Document Two</label>
              <select value={docTwo} onChange={(e) => setDocTwo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors">
                <option value="">Select document</option>
                {docs.map((d) => <option key={d.id} value={d.filename}>{d.filename}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Clause Type</label>
              <select value={clauseType} onChange={(e) => setClauseType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors">
                <option value="">Select clause type</option>
                {CLAUSE_TYPES.map((ct) => <option key={ct} value={ct}>{ct}</option>)}
              </select>
            </div>
            <button onClick={handleCompare} disabled={!canCompare || loading}
              className="px-5 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2">
              {loading ? <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Analyzing...</>
                : <><Scale size={16} /> Compare</>}
            </button>
          </div>

          {sameDoc && (
            <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
              <AlertTriangle size={16} /> Please select two different documents for comparison.
            </div>
          )}

          {error && <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg text-sm text-red-600 dark:text-red-400">{error}</div>}

          {result && (
            <div>
              {result.message ? (
                <div className="text-center py-12 text-gray-400 dark:text-gray-500">
                  <Scale size={40} className="mx-auto mb-3 opacity-50" />
                  <p className="text-sm">{result.message}</p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-end mb-4">
                    <button onClick={exportComparison}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 bg-gray-100 dark:bg-navy-700 rounded-lg hover:bg-gray-200 dark:hover:bg-navy-600 transition-colors">
                      <Download size={14} /> Export
                    </button>
                  </div>
                  <div className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-xl p-6 mb-6 animate-fade-in">
                    <h3 className="text-lg font-semibold text-navy-900 dark:text-amber-400 mb-1">{result.document_one}</h3>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mb-4">vs {result.document_two}</p>
                    <div className="prose prose-sm max-w-none dark:text-gray-300">
                      {result.comparison?.split('\n').map((line, i) => {
                        if (line.startsWith('**') && line.endsWith('**'))
                          return <h4 key={i} className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-4 mb-1">{line.replace(/\*\*/g, '')}</h4>
                        if (line.startsWith('- ') || line.startsWith('* '))
                          return <li key={i} className="text-sm text-gray-700 dark:text-gray-300 ml-4">{line.slice(2)}</li>
                        if (line.trim() === '') return <br key={i} />
                        return <p key={i} className="text-sm text-gray-700 dark:text-gray-300">{line}</p>
                      })}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-50 dark:bg-navy-700/50 border border-gray-200 dark:border-navy-700 rounded-xl p-4">
                      <h4 className="text-sm font-semibold text-navy-900 dark:text-amber-400 mb-2">{result.document_one}</h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Sources: Chunks {result.sources_document_one?.join(', ') || 'N/A'}</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-navy-700/50 border border-gray-200 dark:border-navy-700 rounded-xl p-4">
                      <h4 className="text-sm font-semibold text-navy-900 dark:text-amber-400 mb-2">{result.document_two}</h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Sources: Chunks {result.sources_document_two?.join(', ') || 'N/A'}</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {!result && !loading && !error && !sameDoc && (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400 dark:text-gray-500">
              <Scale size={48} className="mb-3 opacity-50" />
              <p className="text-sm">Select two documents and a clause type, then click Compare</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
