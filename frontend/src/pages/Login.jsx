import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { Scale, Moon, Sun } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/chat')
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-navy-900 px-4 transition-colors">
      <div className="w-full max-w-sm">
        <button
          onClick={toggle}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors"
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-navy-900 dark:bg-amber-400 flex items-center justify-center mx-auto">
            <Scale className="text-white dark:text-navy-900" size={24} />
          </div>
          <h1 className="text-2xl font-bold text-navy-900 dark:text-white mt-3">Welcome back</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Sign in to LexBot</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white dark:bg-navy-800 rounded-xl shadow-sm border border-gray-200 dark:border-navy-700 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="Enter your password"
            />
          </div>

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg font-medium text-sm hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Signing in...</>
            ) : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Don't have an account?{' '}
          <Link to="/register" className="text-navy-900 dark:text-amber-400 font-medium hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  )
}
