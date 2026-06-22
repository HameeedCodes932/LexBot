import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  MessageSquare, FileText, Search, Scale, Shield, LogOut,
  Menu, X, Home, Moon, Sun, CreditCard, Sparkles, ListChecks,
  GitCompare, Library, Users, Key, Settings, History, Bot, User,
} from 'lucide-react'

const links = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/summarize', label: 'Summarize Contract', icon: Sparkles },
  { to: '/extract-clauses', label: 'Clause Extractor', icon: Search },
  { to: '/compare-clauses', label: 'Compare Contracts', icon: Scale },
  { to: '/template-match', label: 'Template Matching', icon: GitCompare },
  { to: '/obligations', label: 'Obligation Tracker', icon: ListChecks },
  { to: '/clause-library', label: 'Clause Library', icon: Library },
  { to: '/agent', label: 'Agent', icon: Bot },
  { to: '/billing', label: 'Billing', icon: CreditCard },
]

export default function Navbar() {
  const { user, isAdmin, logout, branding, isOrgMember, isOrgAdmin } = useAuth()
  const { isDark, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
      isActive
        ? 'bg-navy-700/70 text-white shadow-sm'
        : 'text-gray-400 hover:text-white hover:bg-navy-700/40'
    }`

  const navContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-navy-700/50">
        <Link to="/" className="flex items-center gap-3">
          {branding?.logo_url ? (
            <img src={branding.logo_url} alt="Logo" className="w-9 h-9 rounded-lg object-contain bg-white p-1" />
          ) : (
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-amber-500 flex items-center justify-center shadow-sm">
              <Scale size={18} className="text-navy-900" />
            </div>
          )}
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight leading-tight">
              {branding?.name || 'LexBot'}
            </h1>
            <p className="text-[10px] text-gray-500 leading-tight">Legal AI Assistant</p>
          </div>
        </Link>
      </div>

      {/* User profile card */}
      <Link
        to="/profile"
        onClick={() => setOpen(false)}
        className="flex items-center gap-3 mx-3 mt-3 mb-1 px-3 py-2.5 rounded-lg hover:bg-navy-700/40 transition-colors group"
      >
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400 to-amber-500 flex items-center justify-center text-navy-900 font-bold text-sm shrink-0 shadow-sm overflow-hidden">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
          ) : (
            (user?.username || 'U')[0].toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate group-hover:text-amber-400 transition-colors">{user?.username}</p>
          <p className="text-xs text-gray-500 capitalize truncate">{user?.role} &middot; {user?.firm_name || 'Independent'}</p>
        </div>
        <User size={14} className="text-gray-600 group-hover:text-amber-400 transition-colors shrink-0" />
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto scrollbar-thin">
        <NavLink to="/" end onClick={() => setOpen(false)} className={linkClass}>
          <Home size={18} />
          Home
        </NavLink>

        <div className="pt-3 pb-1">
          <p className="px-3 text-[10px] font-semibold text-gray-600 uppercase tracking-widest">Tools</p>
        </div>
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} onClick={() => setOpen(false)} className={linkClass}>
            <Icon size={18} />
            {label}
          </NavLink>
        ))}

        {isOrgMember && (
          <div className="pt-4 mt-3 border-t border-navy-800/50">
            <p className="px-3 text-[10px] font-semibold text-gray-600 uppercase tracking-widest mb-1.5">Workspace</p>
            <NavLink to="/org/team" onClick={() => setOpen(false)} className={linkClass}>
              <Users size={18} />
              Team Management
            </NavLink>
            <NavLink to="/org/keys" onClick={() => setOpen(false)} className={linkClass}>
              <Key size={18} />
              API Keys
            </NavLink>
            {isOrgAdmin && (
              <>
                <NavLink to="/org/settings" onClick={() => setOpen(false)} className={linkClass}>
                  <Settings size={18} />
                  Org Settings
                </NavLink>
                <NavLink to="/org/audit" onClick={() => setOpen(false)} className={linkClass}>
                  <History size={18} />
                  Audit Logs
                </NavLink>
              </>
            )}
          </div>
        )}

        {isAdmin && (
          <div className="pt-4 mt-3 border-t border-navy-800/50">
            <p className="px-3 text-[10px] font-semibold text-gray-600 uppercase tracking-widest mb-1.5">Admin</p>
            <NavLink to="/admin" onClick={() => setOpen(false)} className={linkClass}>
              <Shield size={18} />
              Admin Dashboard
            </NavLink>
          </div>
        )}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-3 border-t border-navy-700/50 space-y-0.5">
        <button
          onClick={toggle}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-navy-700/40 transition-colors"
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
          {isDark ? 'Light Mode' : 'Dark Mode'}
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-gray-400 hover:text-red-400 hover:bg-navy-700/40 transition-colors"
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </div>
  )

  return (
    <>
      <button
        className="fixed top-4 left-4 z-50 md:hidden bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white p-2.5 rounded-xl shadow-lg hover:scale-105 transition-transform"
        onClick={() => setOpen(!open)}
      >
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>

      {open && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30 md:hidden" onClick={() => setOpen(false)} />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-navy-900 transform transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0 md:min-h-screen`}
      >
        {navContent}
      </aside>
    </>
  )
}
