import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { registerUser } from '../api'
import { useTheme } from '../context/ThemeContext'
import { Scale, Moon, Sun } from 'lucide-react'

export default function Register() {
  const navigate = useNavigate()
  const { isDark, toggle } = useTheme()
  const [form, setForm] = useState({
    username: '', email: '', password: '', confirmPassword: '', firmName: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await registerUser(form.username, form.email, form.password, form.firmName)
      setSuccess('Registration successful! Redirecting to login...')
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-navy-900 px-4 py-12 transition-colors">
      <div className="w-full max-w-sm">
        <button onClick={toggle} className="absolute top-4 right-4 p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors">
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-navy-900 dark:bg-amber-400 flex items-center justify-center mx-auto">
            <Scale className="text-white dark:text-navy-900" size={24} />
          </div>
          <h1 className="text-2xl font-bold text-navy-900 dark:text-white mt-3">Create Account</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Join LexBot</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white dark:bg-navy-800 rounded-xl shadow-sm border border-gray-200 dark:border-navy-700 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Username</label>
            <input type="text" required value={form.username} onChange={update('username')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="johndoe" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input type="email" required value={form.email} onChange={update('email')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="you@example.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Password</label>
            <input type="password" required value={form.password} onChange={update('password')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="Min 8 characters" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Confirm Password</label>
            <input type="password" required value={form.confirmPassword} onChange={update('confirmPassword')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="Repeat your password" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Firm Name</label>
            <input type="text" value={form.firmName} onChange={update('firmName')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-navy-600 rounded-lg text-sm bg-white dark:bg-navy-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-navy-900 dark:focus:ring-amber-400 focus:border-transparent transition-colors"
              placeholder="Your Law Firm" />
          </div>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          {success && <p className="text-sm text-green-600 dark:text-green-400">{success}</p>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg font-medium text-sm hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2">
            {loading ? <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Creating account...</> : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-navy-900 dark:text-amber-400 font-medium hover:underline">Sign In</Link>
        </p>
      </div>
    </div>
  )
}
