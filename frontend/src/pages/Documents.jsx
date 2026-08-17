import { useState, useEffect, useCallback } from 'react'
import { FileText, Upload, Eye, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import WorkspaceTopBar from '../components/WorkspaceTopBar'
import UploadModal from '../components/UploadModal'
import DocumentViewer from '../components/DocumentViewer'
import { TableRowSkeleton } from '../components/LoadingSkeleton'
import { getDocuments } from '../api'
import api from '../api'

export default function Documents() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [viewDoc, setViewDoc] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [deleting, setDeleting] = useState(null)

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getDocuments(page, 20)
      setDocs(data.items || data)
      setTotalPages(data.total_pages || 1)
      setTotal(data.total || 0)
    } catch (err) {
      console.error(err)
    } finally { setLoading(false) }
  }, [page])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const handleDelete = async (docId) => {
    setDeleting(docId)
    try {
      await api.delete(`/api/documents/${docId}`)
      toast.success('Document deleted')
      fetchDocs()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed')
    } finally { setDeleting(null) }
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <WorkspaceTopBar
          title="Documents"
          actions={
            <button
              onClick={() => setShowUpload(true)}
              data-tour="upload"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-xs font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors"
            >
              <Upload size={14} />
              Upload
            </button>
          }
        />

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6">
          {loading ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-navy-700">
                    {['Filename', 'Type', 'Chunks', 'Uploaded', ''].map((h) => (
                      <th key={h} className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[1,2,3,4,5].map((i) => <TableRowSkeleton key={i} cols={5} />)}
                </tbody>
              </table>
            </div>
          ) : docs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400 dark:text-gray-500">
              <FileText size={48} className="mb-3 opacity-50" />
              <p className="text-sm">No documents uploaded yet.</p>
              <button onClick={() => setShowUpload(true)} className="mt-3 text-sm text-navy-900 dark:text-amber-400 font-medium hover:underline">
                Upload your first document
              </button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-navy-700">
                      <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Filename</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Type</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Chunks</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Uploaded</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500 dark:text-gray-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.map((doc) => (
                      <tr key={doc.id} className="border-b border-gray-100 dark:border-navy-700 hover:bg-gray-50 dark:hover:bg-navy-800/50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <FileText size={14} className="text-gray-400 flex-shrink-0" />
                            <span className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]">{doc.filename}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-gray-600 dark:text-gray-400 capitalize">{doc.doc_type || 'General'}</td>
                        <td className="py-3 px-4 text-right text-gray-600 dark:text-gray-400">{doc.chunks}</td>
                        <td className="py-3 px-4 text-right text-gray-500 dark:text-gray-400 text-xs">
                          {doc.uploaded_at ? new Date(doc.uploaded_at + 'Z').toLocaleDateString() : '—'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => setViewDoc(doc)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 hover:text-navy-900 dark:hover:text-amber-400 transition-colors"
                              title="View"
                            >
                              <Eye size={14} />
                            </button>
                            <button
                              onClick={() => handleDelete(doc.id)}
                              disabled={deleting === doc.id}
                              className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                              title="Delete"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-navy-700">
                  <p className="text-xs text-gray-500 dark:text-gray-400">{total} document{total !== 1 ? 's' : ''}</p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 disabled:opacity-30 transition-colors"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <span className="text-xs text-gray-600 dark:text-gray-400 font-medium">Page {page} of {totalPages}</span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                      className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 disabled:opacity-30 transition-colors"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onSuccess={fetchDocs} />}
      {viewDoc && <DocumentViewer filename={viewDoc.filename} onClose={() => setViewDoc(null)} />}
    </div>
  )
}
