import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { loginUser, getMe, getBranding } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('lexbot_token'))
  const [loading, setLoading] = useState(true)
  const [branding, setBranding] = useState({
    name: 'LexBot',
    logo_url: null,
    primary_color: '#0f172a', // Slate 900
    secondary_color: '#3b82f6', // Blue 500
    sso_enabled: false,
  })

  // Load branding dynamically based on domain or custom domain
  const loadBranding = useCallback(async () => {
    try {
      const brand = await getBranding(null, window.location.hostname)
      if (brand) {
        setBranding({
          name: brand.name || 'LexBot',
          logo_url: brand.logo_url,
          primary_color: brand.primary_color || '#0f172a',
          secondary_color: brand.secondary_color || '#3b82f6',
          sso_enabled: brand.sso_enabled || false,
        })
        
        // Dynamically apply colors to document root
        document.documentElement.style.setProperty('--color-primary', brand.primary_color || '#0f172a')
        document.documentElement.style.setProperty('--color-secondary', brand.secondary_color || '#3b82f6')
      }
    } catch (err) {
      console.warn('Failed to load branding info', err)
    }
  }, [])

  useEffect(() => {
    loadBranding()
  }, [loadBranding])

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('lexbot_token')
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  const login = useCallback(async (email, password) => {
    const data = await loginUser(email, password)
    localStorage.setItem('lexbot_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('lexbot_token')
    setToken(null)
    setUser(null)
    window.location.href = '/login'
  }, [])

  const isAdmin = user?.role === 'admin'
  const isOrgMember = !!user?.org_id
  const isOrgAdmin = user?.org_role === 'owner' || user?.org_role === 'admin'
  const isOrgOwner = user?.org_role === 'owner'

  return (
    <AuthContext.Provider value={{ 
      user, token, loading, login, logout, isAdmin, 
      branding, isOrgMember, isOrgAdmin, isOrgOwner, setToken, setUser 
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
