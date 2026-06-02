import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  MessageSquare, FileText, Search, Scale, Shield, LogOut, Trash2,
  Menu, X, Home, Moon, Sun, CreditCard, Sparkles, ListChecks,
  GitCompare, Library, Users, Key, Settings, History,
} from 'lucide-react'
import DeleteDataModal from './DeleteDataModal'

const links = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/summarize', label: 'Summarize Contract', icon: Sparkles },
  { to: '/extract-clauses', label: 'Clause Extractor', icon: Search },
  { to: '/compare-clauses', label: 'Compare Contracts', icon: Scale },
  { to: '/template-match', label: 'Template Matching', icon: GitCompare },
  { to: '/obligations', label: 'Obligation Tracker', icon: ListChecks },
  { to: '/clause-library', label: 'Clause Library', icon: Library },
  { to: '/billing', label: 'Billing', icon: CreditCard },
]

export default function Navbar() {
  const { user, isAdmin, logout, branding, isOrgMember, isOrgAdmin } = useAuth()
  const { isDark, toggle } = useTheme()
  const [open, setOpen] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)

  const navContent = (
    <div className="flex flex-col h-full">
      <div className="px-5 py-6 border-b border-navy-700">
        <Link to="/" className="flex items-center gap-2 mb-1">
          {branding?.logo_url ? (
            <img src={branding.logo_url} alt="Logo" className="w-8 h-8 rounded-lg object-contain bg-white p-0.5" />
          ) : (
            <div className="w-8 h-8 rounded-lg bg-amber-400 flex items-center justify-center">
              <Scale size={16} className="text-navy-900" />
            </div>
          )}
          <h1 className="text-xl font-bold text-white tracking-tight">
            {branding?.name || 'LexBot'}
          </h1>
        </Link>
        <p className="text-xs text-gray-400 mt-0.5 ml-10">Legal AI Assistant</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <NavLink
          to="/"
          end
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? 'bg-navy-700 text-white'
                : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
            }`
          }
        >
          <Home size={18} />
          Home
        </NavLink>
        
        <div className="space-y-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-navy-700 text-white'
                    : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>

        {isOrgMember && (
          <div className="pt-4 border-t border-navy-800 space-y-1 mt-4">
            <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Workspace</p>
            <NavLink
              to="/org/team"
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-navy-700 text-white'
                    : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
                }`
              }
            >
              <Users size={18} />
              Team Management
            </NavLink>
            <NavLink
              to="/org/keys"
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-navy-700 text-white'
                    : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
                }`
              }
            >
              <Key size={18} />
              API Keys
            </NavLink>
            {isOrgAdmin && (
              <>
                <NavLink
                  to="/org/settings"
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-navy-700 text-white'
                        : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
                    }`
                  }
                >
                  <Settings size={18} />
                  Org Settings
                </NavLink>
                <NavLink
                  to="/org/audit"
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-navy-700 text-white'
                        : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
                    }`
                  }
                >
                  <History size={18} />
                  Audit Logs
                </NavLink>
              </>
            )}
          </div>
        )}

        {isAdmin && (
          <NavLink
            to="/admin"
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-navy-700 text-white'
                  : 'text-gray-300 hover:bg-navy-700/50 hover:text-white'
              }`
            }
          >
            <Shield size={18} />
            Admin Dashboard
          </NavLink>
        )}
      </nav>

      <div className="px-4 py-4 border-t border-navy-700 space-y-2">
        <button
          onClick={toggle}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-navy-700 rounded-lg transition-colors"
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
          {isDark ? 'Light Mode' : 'Dark Mode'}
        </button>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 font-bold text-sm">
            {(user?.username || 'U')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.username}</p>
            <p className="text-xs text-gray-400 capitalize">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={() => setDeleteModalOpen(true)}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-navy-700 rounded-lg transition-colors"
        >
          <Trash2 size={16} />
          Delete My Data
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-navy-700 rounded-lg transition-colors"
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </div>
  )
  const modals = (
    <DeleteDataModal open={deleteModalOpen} onClose={() => setDeleteModalOpen(false)} />
  )

  return (
    <>
      <button
        className="fixed top-4 left-4 z-50 md:hidden bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white p-2 rounded-lg shadow-lg"
        onClick={() => setOpen(!open)}
      >
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-navy-900 transform transition-transform duration-200 ease-in-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 md:min-h-screen`}
      >
        {navContent}
      </aside>
      {modals}
    </>
  )
}
