import { createContext, useContext, useEffect, useState, useCallback } from 'react'

const LayoutContext = createContext(null)

export function LayoutProvider({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window === 'undefined') return true
    return window.innerWidth >= 768
  })
  const [sessionsOpen, setSessionsOpen] = useState(false)

  const closeSidebar = useCallback(() => setSidebarOpen(false), [])
  const toggleSidebar = useCallback(() => setSidebarOpen((o) => !o), [])
  const closeSessions = useCallback(() => setSessionsOpen(false), [])
  const toggleSessions = useCallback(() => setSessionsOpen((o) => !o), [])

  // Panels collapse automatically on small screens
  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false)
        setSessionsOpen(false)
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Escape closes the open workspace panels
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setSidebarOpen(false)
        setSessionsOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <LayoutContext.Provider
      value={{
        sidebarOpen,
        sessionsOpen,
        setSidebarOpen,
        setSessionsOpen,
        closeSidebar,
        closeSessions,
        toggleSidebar,
        toggleSessions,
      }}
    >
      {children}
    </LayoutContext.Provider>
  )
}

export function useLayout() {
  const ctx = useContext(LayoutContext)
  if (!ctx) throw new Error('useLayout must be used within a LayoutProvider')
  return ctx
}
