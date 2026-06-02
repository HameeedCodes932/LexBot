import { Link } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { DPA as DPAContent, LEGAL } from '../legalContent'

export default function DPA() {
  return (
    <div className="min-h-screen bg-white dark:bg-navy-900">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-navy-900/80 backdrop-blur-md border-b border-gray-200 dark:border-navy-700">
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
        <h1 className="text-3xl font-bold text-navy-900 dark:text-white mb-2">Data Processing Agreement</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">Last updated: {DPAContent.last_updated}</p>

        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-8">
          <p className="text-sm text-amber-800 dark:text-amber-300">
            <strong>Parties:</strong> Data Controller — {DPAContent.parties.controller}. Data Processor — {DPAContent.parties.processor}.
          </p>
        </div>

        <div className="space-y-6">
          {DPAContent.sections.map((section, i) => (
            <div key={i}>
              <h2 className="text-xl font-semibold text-navy-900 dark:text-white mb-2">{section.title}</h2>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{section.content}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 pt-8 border-t border-gray-200 dark:border-navy-700">
          <h2 className="text-xl font-semibold text-navy-900 dark:text-white mb-6">Schedules</h2>
          {DPAContent.schedules.map((schedule, i) => (
            <div key={i} className="mb-6">
              <h3 className="text-lg font-semibold text-navy-900 dark:text-white mb-2">{schedule.title}</h3>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{schedule.content}</p>
            </div>
          ))}
        </div>

        <p className="mt-10 text-sm text-gray-500 dark:text-gray-400">
          To execute this DPA, contact us at <a href={`mailto:${LEGAL.contact_email}`} className="text-amber-600 dark:text-amber-400 hover:underline">{LEGAL.contact_email}</a>
        </p>
      </div>
    </div>
  )
}
