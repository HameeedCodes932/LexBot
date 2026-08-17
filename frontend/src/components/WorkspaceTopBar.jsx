import { PanelLeft, PanelLeftClose, History } from 'lucide-react'
import { useLayout } from '../context/LayoutContext'

export default function WorkspaceTopBar({ title, titleProps, actions, showSessionsToggle }) {
  const { sidebarOpen, toggleSidebar, sessionsOpen, toggleSessions } = useLayout()

  const iconBtn =
    'p-1.5 rounded-md text-gray-500 dark:text-gray-400 hover:text-navy-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-navy-700 transition-colors'

  return (
    <div className="flex items-center justify-between gap-2 min-h-12 shrink-0 px-3 md:px-4 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
      <div className="flex items-center gap-0.5 min-w-0">
        <button
          onClick={toggleSidebar}
          className={iconBtn}
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
        </button>
        {showSessionsToggle && (
          <button
            onClick={toggleSessions}
            className={`${iconBtn} ${
              sessionsOpen
                ? 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20'
                : ''
            }`}
            title={sessionsOpen ? 'Hide sessions' : 'Show sessions'}
            aria-label="Toggle sessions panel"
          >
            <History size={18} />
          </button>
        )}
        {title && (
          <h2
            {...titleProps}
            className="ml-1.5 text-sm font-semibold text-gray-900 dark:text-white truncate"
          >
            {title}
          </h2>
        )}
      </div>
      {actions && <div className="flex items-center gap-1.5 shrink-0 min-w-0">{actions}</div>}
    </div>
  )
}
