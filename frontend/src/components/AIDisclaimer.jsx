import { AlertTriangle } from 'lucide-react'
import { AI_DISCLAIMER_TEXT, DISCLAIMER_SHORT_TEXT } from '../legalContent'

export function AIDisclaimerBanner() {
  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 flex items-start gap-3">
      <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-amber-800 dark:text-amber-300">AI Disclaimer</p>
        <p className="text-xs text-amber-700 dark:text-amber-400 mt-1 leading-relaxed">{AI_DISCLAIMER_TEXT}</p>
      </div>
    </div>
  )
}

export function AIDisclaimerInline() {
  return (
    <p className="text-xs text-gray-400 dark:text-gray-500 italic text-center mt-4 px-4">
      {DISCLAIMER_SHORT_TEXT}
    </p>
  )
}

export function AIDisclaimerChatNotice() {
  return (
    <div className="bg-amber-50/80 dark:bg-amber-900/10 border border-amber-200/60 dark:border-amber-800/40 rounded-lg px-4 py-2.5 flex items-start gap-2 my-2">
      <AlertTriangle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
      <p className="text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
        {DISCLAIMER_SHORT_TEXT}
      </p>
    </div>
  )
}
