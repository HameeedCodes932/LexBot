import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import {
  Scale, MessageSquare, FileText, Search, Shield,
  ChevronRight, Star, Moon, Sun, ArrowRight, Bot,
} from 'lucide-react'
import Footer from '../components/Footer'
import { AIDisclaimerBanner } from '../components/AIDisclaimer'

const FEATURES = [
  { icon: MessageSquare, title: 'Smart Chat', desc: 'Ask natural language questions about your legal documents. Get answers with source citations.' },
  { icon: Search, title: 'Clause Extraction', desc: 'Extract specific clauses like indemnification, termination, and payment from any contract.' },
  { icon: Scale, title: 'Contract Comparison', desc: 'Compare clauses side-by-side across two contracts with AI-powered analysis.' },
  { icon: Shield, title: 'Risk Detection', desc: 'Automatically flag risky terms like unlimited liability, auto-renewal, and unilateral modification.' },
]

const TESTIMONIALS = [
  { name: 'Sarah Chen', role: 'Corporate Counsel', text: '"LexBot cut our contract review time by 60%. The clause extraction is incredibly accurate."' },
  { name: 'Marcus Rivera', role: 'Solo Practitioner', text: '"Finally, an AI tool that understands legal language. The source citations give me confidence in every answer."' },
  { name: 'Emily Park', role: 'Legal Ops Manager', text: '"We onboarded our entire department in one afternoon. The comparison feature is a game-changer for M&A work."' },
]

const PRICING = [
  {
    name: 'Starter', price: '$29', period: '/month', desc: 'For solo practitioners',
    features: ['50 document uploads/mo', '1,000 chat queries/mo', 'Clause extraction', 'Email support'],
  },
  {
    name: 'Professional', price: '$79', period: '/month', desc: 'For growing firms',
    features: ['Unlimited uploads', '10,000 chat queries/mo', 'Contract comparison', 'Priority support', 'API access'],
    popular: true,
  },
  {
    name: 'Enterprise', price: '$199', period: '/month', desc: 'For large organizations',
    features: ['Everything in Pro', 'Unlimited queries', 'Custom branding', 'SSO & SAML', 'Dedicated account manager'],
  },
]

export default function Landing() {
  const { user } = useAuth()
  const { isDark, toggle } = useTheme()

  return (
    <div className="min-h-screen bg-white dark:bg-navy-900">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white dark:bg-navy-900 border-b border-gray-200 dark:border-navy-700">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-navy-900 dark:bg-amber-400 flex items-center justify-center">
              <Scale size={18} className="text-white dark:text-navy-900" />
            </div>
            <span className="text-lg font-bold text-navy-900 dark:text-white">LexBot</span>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={toggle} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-500 dark:text-gray-400 transition-colors">
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {user ? (
              <Link to="/chat" className="px-4 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors">
                Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-navy-900 dark:hover:text-white transition-colors">
                  Sign In
                </Link>
                <Link to="/register" className="px-4 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors">
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-20 pb-16 md:pt-32 md:pb-24">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-full text-xs font-medium text-amber-700 dark:text-amber-300 mb-6">
            <Bot size={12} />
            AI-Powered Legal Document Assistant
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold text-navy-900 dark:text-white leading-tight mb-4">
            Your Documents,{' '}
            <span className="text-amber-500">Supercharged</span>
          </h1>
          <p className="text-lg md:text-xl text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
            Upload legal documents, ask questions in plain English, extract clauses, and compare contracts — all powered by AI that understands legal language.
          </p>
          <div className="flex items-center justify-center gap-3">
            {user ? (
              <Link to="/chat" className="px-6 py-3 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-xl text-sm font-semibold hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors flex items-center gap-2 shadow-lg shadow-navy-900/20 dark:shadow-amber-400/20">
                Go to Dashboard <ArrowRight size={16} />
              </Link>
            ) : (
              <Link to="/register" className="px-6 py-3 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-xl text-sm font-semibold hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors flex items-center gap-2 shadow-lg shadow-navy-900/20 dark:shadow-amber-400/20">
                Start Free Trial <ArrowRight size={16} />
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-gray-50 dark:bg-navy-800/50 py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-center text-navy-900 dark:text-white mb-12">
            Everything you need to manage legal documents
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                <div className="w-10 h-10 rounded-lg bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-navy-900 dark:text-amber-400 mb-4">
                  <f.icon size={20} />
                </div>
                <h3 className="text-base font-semibold text-navy-900 dark:text-white mb-1">{f.title}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-center text-navy-900 dark:text-white mb-12">
            Trusted by legal professionals
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6">
                <div className="flex gap-0.5 mb-3">
                  {[1,2,3,4,5].map((i) => <Star key={i} size={14} className="fill-amber-400 text-amber-400" />)}
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 leading-relaxed">{t.text}</p>
                <div>
                  <p className="text-sm font-semibold text-navy-900 dark:text-white">{t.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-gray-50 dark:bg-navy-800/50 py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl md:text-3xl font-bold text-center text-navy-900 dark:text-white mb-12">
            Simple, transparent pricing
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {PRICING.map((p) => (
              <div
                key={p.name}
                className={`relative bg-white dark:bg-navy-800 rounded-xl border-2 p-6 transition-all duration-200 hover:shadow-lg ${
                  p.popular
                    ? 'border-navy-900 dark:border-amber-400 shadow-navy-900/10 dark:shadow-amber-400/10'
                    : 'border-gray-200 dark:border-navy-700'
                }`}
              >
                {p.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-navy-900 dark:bg-amber-400 text-white dark:text-navy-900 text-xs font-semibold rounded-full">
                    Most Popular
                  </span>
                )}
                <h3 className="text-lg font-bold text-navy-900 dark:text-white mb-1">{p.name}</h3>
                <div className="flex items-baseline gap-0.5 mb-1">
                  <span className="text-3xl font-extrabold text-navy-900 dark:text-white">{p.price}</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{p.period}</span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{p.desc}</p>
                <ul className="space-y-2 mb-6">
                  {p.features.map((f) => (
                    <li key={f} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                      <ChevronRight size={14} className="text-amber-500 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className={`block text-center px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
                    p.popular
                      ? 'bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white hover:bg-navy-800 dark:hover:bg-amber-500'
                      : 'bg-gray-100 dark:bg-navy-700 text-gray-900 dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-navy-600'
                  }`}
                >
                  {user ? 'Get Started' : 'Start Free Trial'}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Disclaimer */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <AIDisclaimerBanner />
      </section>

      {/* CTA */}
      <section className="py-16 md:py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl md:text-4xl font-bold text-navy-900 dark:text-white mb-4">
            Ready to transform your document workflow?
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            Join thousands of legal professionals who use LexBot to work smarter, not harder.
          </p>
          {user ? (
            <Link to="/chat" className="inline-flex items-center gap-2 px-6 py-3 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-xl text-sm font-semibold hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors shadow-lg shadow-navy-900/20">
              Go to Dashboard <ArrowRight size={16} />
            </Link>
          ) : (
            <Link to="/register" className="inline-flex items-center gap-2 px-6 py-3 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-xl text-sm font-semibold hover:bg-navy-800 dark:hover:bg-amber-500 transition-colors shadow-lg shadow-navy-900/20">
              Start Free Trial <ArrowRight size={16} />
            </Link>
          )}
        </div>
      </section>

      <Footer />
    </div>
  )
}
