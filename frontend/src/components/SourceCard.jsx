import { FileText } from 'lucide-react'

export default function SourceCard({ document, chunk_index, preview }) {
  return (
    <div className="flex gap-2 bg-gray-50 dark:bg-navy-700/50 border border-gray-200 dark:border-navy-700 rounded-lg p-3 text-xs">
      <FileText size={14} className="text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <p className="font-medium text-gray-700 dark:text-gray-300 truncate">
          {document} — Chunk {chunk_index}
        </p>
        <p className="text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{preview}</p>
      </div>
    </div>
  )
}
