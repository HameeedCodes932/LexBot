import { useState, useEffect } from 'react'
import { X, Cookie } from 'lucide-react'

const COOKIE_CONSENT_KEY = 'lexbot_cookie_consent'

export default function CookieConsent() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY)
    if (!stored) {
      const timer = setTimeout(() => setVisible(true), 1000)
      return () => clearTimeout(timer)
    }
  }, [])

  function acceptAll() {
    localStorage.setItem(COOKIE_CONSENT_KEY, 'all')
    setVisible(false)
  }

  function acceptEssential() {
    localStorage.setItem(COOKIE_CONSENT_KEY, 'essential')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-navy-800 border-t border-gray-200 dark:border-navy-700 shadow-xl">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-start gap-3 flex-1">
          <Cookie size={20} className="text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-navy-900 dark:text-white">Cookie Consent</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              We use essential cookies for authentication and security. Analytics cookies help us improve.
              Read our{' '}
              <a href="/privacy" className="text-amber-600 dark:text-amber-400 hover:underline">Privacy Policy</a>.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={acceptEssential}
            className="px-3 py-2 text-xs font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-navy-600 rounded-lg hover:bg-gray-50 dark:hover:bg-navy-700 transition-colors"
          >
            Essential Only
          </button>
          <button
            onClick={acceptAll}
            className="px-4 py-2 text-xs font-medium bg-navy-900 dark:bg-amber-400 text-white dark:text-navy-900 rounded-lg hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors"
          >
            Accept All
          </button>
          <button
            onClick={acceptEssential}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
