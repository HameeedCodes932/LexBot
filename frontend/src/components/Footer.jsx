import { Link } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { LEGAL } from '../legalContent'

export default function Footer() {
  return (
    <footer className="bg-gray-50 dark:bg-navy-900 border-t border-gray-200 dark:border-navy-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-navy-900 dark:bg-amber-400 flex items-center justify-center">
                <Scale size={14} className="text-white dark:text-navy-900" />
              </div>
              <span className="text-base font-bold text-navy-900 dark:text-white">LexBot</span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
              AI-powered legal document analysis for modern law firms.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Product</h3>
            <ul className="space-y-2">
              <li><Link to="/" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">Home</Link></li>
              <li><Link to="/login" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">Sign In</Link></li>
              <li><Link to="/register" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">Get Started</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Legal</h3>
            <ul className="space-y-2">
              <li><Link to="/terms" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">Terms of Service</Link></li>
              <li><Link to="/privacy" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">Privacy Policy</Link></li>
              <li><Link to="/dpa" className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">DPA</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Contact</h3>
            <ul className="space-y-2">
              <li><a href={`mailto:${LEGAL.contact_email}`} className="text-sm text-gray-700 dark:text-gray-300 hover:text-amber-600 dark:hover:text-amber-400 transition-colors">{LEGAL.contact_email}</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-navy-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            &copy; {new Date().getFullYear()} LexBot Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <Link to="/terms" className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">Terms</Link>
            <Link to="/privacy" className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">Privacy</Link>
            <Link to="/dpa" className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">DPA</Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
