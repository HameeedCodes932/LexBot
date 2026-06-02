import { useState, useRef } from 'react'
import { Upload, X, File, CheckCircle } from 'lucide-react'
import { uploadDocument } from '../api'

const ALLOWED = ['txt', 'pdf', 'docx']

export default function UploadModal({ onClose, onSuccess }) {
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  const validate = (f) => {
    const ext = f.name.split('.').pop().toLowerCase()
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported file type ".${ext}". Allowed: txt, pdf, docx.`)
      return false
    }
    if (f.size === 0) {
      setError('File is empty.')
      return false
    }
    setError('')
    return true
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f && validate(f)) setFile(f)
  }

  const handleSelect = (e) => {
    const f = e.target.files[0]
    if (f && validate(f)) setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const data = await uploadDocument(file)
      setResult(data)
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-navy-800 rounded-xl shadow-2xl w-full max-w-md mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Upload Document</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X size={20} />
          </button>
        </div>

        {!result ? (
          <>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                file
                  ? 'border-navy-900 dark:border-amber-400 bg-navy-50 dark:bg-navy-700/50'
                  : 'border-gray-300 dark:border-navy-600 hover:border-gray-400 dark:hover:border-navy-500 bg-gray-50 dark:bg-navy-700/30'
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".txt,.pdf,.docx"
                className="hidden"
                onChange={handleSelect}
              />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-navy-900 dark:text-amber-400">
                  <File size={24} />
                  <div className="text-left">
                    <p className="font-medium text-sm text-gray-900 dark:text-gray-100">{file.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <Upload size={32} className="mx-auto text-gray-400 dark:text-gray-500 mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Drag & drop or <span className="text-navy-900 dark:text-amber-400 font-medium">browse</span>
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    .txt, .pdf, .docx only
                  </p>
                </div>
              )}
            </div>

            {error && (
              <p className="text-sm text-red-600 dark:text-red-400 mt-3">{error}</p>
            )}

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="mt-4 w-full py-2.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg font-medium text-sm hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {uploading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Uploading...
                </>
              ) : (
                'Upload'
              )}
            </button>
          </>
        ) : (
          <div className="text-center py-6">
            <CheckCircle size={40} className="mx-auto text-green-500 mb-2" />
            <p className="font-medium text-gray-900 dark:text-white">
              Ingested {result.chunks} chunks
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{result.filename}</p>
          </div>
        )}
      </div>
    </div>
  )
}
