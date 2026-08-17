import { NavLink, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useLayout } from '../context/LayoutContext'
import {
  MessageSquare, FileText, Search, Scale, Shield, LogOut,
  Home, Moon, Sun, CreditCard, Sparkles, ListChecks,
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
  const { sidebarOpen, closeSidebar } = useLayout()

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-gray-100 text-navy-900 dark:bg-navy-800 dark:text-white'
        : 'text-gray-500 hover:text-navy-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-navy-800'
    }`

  const sectionLabel = 'px-3 text-[10px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest'

  const navContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-200 dark:border-navy-800">
        <Link to="/" onClick={closeSidebar} className="flex items-center gap-3">
          {branding?.logo_url ? (
            <img src={branding.logo_url} alt="Logo" className="w-9 h-9 rounded-lg object-contain bg-white p-1" />
          ) : (
            <div className="w-9 h-9 rounded-lg bg-amber-400 flex items-center justify-center">
              <Scale size={18} className="text-navy-900" />
            </div>
          )}
          <div>
            <h1 className="text-base font-bold text-navy-900 dark:text-white tracking-tight leading-tight">
              {branding?.name || 'LexBot'}
            </h1>
            <p className="text-[10px] text-gray-400 dark:text-gray-500 leading-tight">Legal AI Assistant</p>
          </div>
        </Link>
      </div>

      {/* User profile card */}
      <Link
        to="/profile"
        onClick={closeSidebar}
        className="flex items-center gap-3 mx-3 mt-3 mb-1 px-3 py-2 rounded-md hover:bg-gray-100 dark:hover:bg-navy-800 transition-colors group"
      >
        <div className="w-8 h-8 rounded-full bg-amber-400 flex items-center justify-center text-navy-900 font-bold text-sm shrink-0 overflow-hidden">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
          ) : (
            (user?.username || 'U')[0].toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-navy-900 dark:text-white truncate">{user?.username}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 capitalize truncate">{user?.role} &middot; {user?.firm_name || 'Independent'}</p>
        </div>
        <User size={14} className="text-gray-300 dark:text-gray-600 shrink-0" />
      </Link>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto scrollbar-thin">
        <NavLink to="/" end onClick={closeSidebar} className={linkClass}>
          <Home size={18} />
          Home
        </NavLink>

        <div className="pt-3 pb-1">
          <p className={sectionLabel}>Tools</p>
        </div>
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} onClick={closeSidebar} className={linkClass}>
            <Icon size={18} />
            {label}
          </NavLink>
        ))}

        {isOrgMember && (
          <div className="pt-4 mt-3 border-t border-gray-200 dark:border-navy-800">
            <p className={`${sectionLabel} mb-1.5`}>Workspace</p>
            <NavLink to="/org/team" onClick={closeSidebar} className={linkClass}>
              <Users size={18} />
              Team Management
            </NavLink>
            <NavLink to="/org/keys" onClick={closeSidebar} className={linkClass}>
              <Key size={18} />
              API Keys
            </NavLink>
            {isOrgAdmin && (
              <>
                <NavLink to="/org/settings" onClick={closeSidebar} className={linkClass}>
                  <Settings size={18} />
                  Org Settings
                </NavLink>
                <NavLink to="/org/audit" onClick={closeSidebar} className={linkClass}>
                  <History size={18} />
                  Audit Logs
                </NavLink>
              </>
            )}
          </div>
        )}

        {isAdmin && (
          <div className="pt-4 mt-3 border-t border-gray-200 dark:border-navy-800">
            <p className={`${sectionLabel} mb-1.5`}>Admin</p>
            <NavLink to="/admin" onClick={closeSidebar} className={linkClass}>
              <Shield size={18} />
              Admin Dashboard
            </NavLink>
          </div>
        )}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-3 border-t border-gray-200 dark:border-navy-800 space-y-0.5">
        <button
          onClick={toggle}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm text-gray-500 hover:text-navy-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-navy-800 transition-colors"
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
          {isDark ? 'Light Mode' : 'Dark Mode'}
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-md text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/20 transition-colors"
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop: in-flow column, collapses to zero width */}
      <aside
        className={`hidden md:block md:min-h-screen shrink-0 overflow-hidden bg-white dark:bg-navy-900 transition-[width] duration-200 ${
          sidebarOpen
            ? 'w-64 border-r border-gray-200 dark:border-navy-800'
            : 'w-0 border-transparent'
        }`}
      >
        <div className="w-64 h-full flex flex-col">{navContent}</div>
      </aside>

      {/* Mobile: overlay drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={closeSidebar} />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-200 md:hidden ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="w-64 h-full flex flex-col bg-white dark:bg-navy-900 border-r border-gray-200 dark:border-navy-800">
          {navContent}
        </div>
      </aside>
    </>
  )
}
