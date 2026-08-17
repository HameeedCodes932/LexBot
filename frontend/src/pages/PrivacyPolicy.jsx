import { Link } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { PRIVACY_POLICY, LEGAL } from '../legalContent'

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white dark:bg-navy-900">
      <nav className="sticky top-0 z-50 bg-white dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-navy-900 dark:bg-amber-400 flex items-center justify-center">
              <Scale size={18} className="text-white dark:text-navy-900" />
            </div>
            <span className="text-lg font-bold text-navy-900 dark:text-white">LexBot</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-navy-900 dark:hover:text-white transition-colors">Sign In</Link>
            <Link to="/register" className="px-4 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors">Get Started</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        <h1 className="text-3xl font-bold text-navy-900 dark:text-white mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Last updated: {PRIVACY_POLICY.last_updated}</p>

        <div className="space-y-6">
          {PRIVACY_POLICY.sections.map((section, i) => (
            <div key={i}>
              <h2 className="text-xl font-semibold text-navy-900 dark:text-white mb-2">{section.title}</h2>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{section.content}</p>
            </div>
          ))}
        </div>

        <p className="mt-10 text-sm text-gray-500 dark:text-gray-400">
          Questions? Contact our DPO at <a href={`mailto:${LEGAL.contact_email}`} className="text-amber-600 dark:text-amber-400 hover:underline">{LEGAL.contact_email}</a>
        </p>
      </div>
    </div>
  )
}
