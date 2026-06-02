export function MessageSkeleton() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-8 h-8 rounded-full skeleton flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-4 skeleton w-3/4" />
        <div className="h-4 skeleton w-1/2" />
        <div className="h-4 skeleton w-2/3" />
      </div>
    </div>
  )
}

export function TableRowSkeleton({ cols = 4 }) {
  return (
    <tr className="border-b border-gray-100 dark:border-navy-700">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <div className="h-4 skeleton" style={{ width: `${60 + Math.random() * 40}%` }} />
        </td>
      ))}
    </tr>
  )
}

export function StatCardSkeleton() {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg skeleton" />
      <div className="space-y-2">
        <div className="h-6 w-16 skeleton" />
        <div className="h-3 w-20 skeleton" />
      </div>
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4 space-y-3">
      <div className="h-5 w-2/3 skeleton" />
      <div className="h-4 w-full skeleton" />
      <div className="h-4 w-3/4 skeleton" />
    </div>
  )
}
