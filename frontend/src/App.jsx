import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { ToastProvider } from './components/Toast'
import OnboardingTour from './components/OnboardingTour'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import ClauseExtractor from './pages/ClauseExtractor'
import ContractComparison from './pages/ContractComparison'
import DocumentSummary from './pages/DocumentSummary'
import ObligationTracker from './pages/ObligationTracker'
import TemplateMatch from './pages/TemplateMatch'
import ClauseLibrary from './pages/ClauseLibrary'
import Agent from './pages/Agent'
import AdminDashboard from './pages/AdminDashboard'
import TeamManagement from './pages/TeamManagement'
import AuditLogs from './pages/AuditLogs'
import APIKeys from './pages/APIKeys'
import OrgSettings from './pages/OrgSettings'
import TermsOfService from './pages/TermsOfService'
import PrivacyPolicy from './pages/PrivacyPolicy'
import DPA from './pages/DPA'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import CookieConsent from './components/CookieConsent'

function Spinner() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-navy-900">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-navy-900 dark:border-amber-400 border-t-transparent" />
    </div>
  )
}

function AppRoutes() {
  const { loading } = useAuth()

  if (loading) return <Spinner />

  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
        <Route path="/documents" element={<ProtectedRoute><Documents /></ProtectedRoute>} />
        <Route path="/extract-clauses" element={<ProtectedRoute><ClauseExtractor /></ProtectedRoute>} />
        <Route path="/compare-clauses" element={<ProtectedRoute><ContractComparison /></ProtectedRoute>} />
        <Route path="/summarize" element={<ProtectedRoute><DocumentSummary /></ProtectedRoute>} />
        <Route path="/obligations" element={<ProtectedRoute><ObligationTracker /></ProtectedRoute>} />
        <Route path="/template-match" element={<ProtectedRoute><TemplateMatch /></ProtectedRoute>} />
        <Route path="/clause-library" element={<ProtectedRoute><ClauseLibrary /></ProtectedRoute>} />
        <Route path="/agent" element={<ProtectedRoute><Agent /></ProtectedRoute>} />
        <Route path="/org/team" element={<ProtectedRoute><TeamManagement /></ProtectedRoute>} />
        <Route path="/org/audit" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />
        <Route path="/org/keys" element={<ProtectedRoute><APIKeys /></ProtectedRoute>} />
        <Route path="/org/settings" element={<ProtectedRoute><OrgSettings /></ProtectedRoute>} />
        <Route path="/admin" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/dpa" element={<DPA />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <CookieConsent />
      <OnboardingTour />
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider />
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  )
}
