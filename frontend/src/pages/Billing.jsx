import { useState, useEffect } from 'react'
import { CreditCard, Shield, Zap, Check, X, ArrowUp, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import Navbar from '../components/Navbar'
import { CardSkeleton } from '../components/LoadingSkeleton'
import { getSubscription, createCheckoutSession, createPortalSession, getInvoices } from '../api'

const PLAN_META = {
  free: { name: 'Free', color: 'bg-gray-100 dark:bg-navy-700 text-gray-700 dark:text-gray-300' },
  pro: { name: 'Professional', color: 'bg-navy-100 dark:bg-navy-700 text-navy-900 dark:text-amber-400' },
  enterprise: { name: 'Enterprise', color: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300' },
}

export default function Billing() {
  const [data, setData] = useState(null)
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)

  useEffect(() => {
    Promise.all([getSubscription(), getInvoices()])
      .then(([sub, inv]) => {
        setData(sub)
        setInvoices(inv)
      })
      .catch(() => toast.error('Failed to load billing info'))
      .finally(() => setLoading(false))
  }, [])

  const handleUpgrade = async () => {
    setActionLoading('upgrade')
    try {
      const { url } = await createCheckoutSession(window.location.origin)
      window.location.href = url
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Checkout unavailable')
    } finally { setActionLoading(null) }
  }

  const handlePortal = async () => {
    setActionLoading('portal')
    try {
      const { url } = await createPortalSession(window.location.origin)
      window.location.href = url
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Portal unavailable')
    } finally { setActionLoading(null) }
  }

  const plan = data?.plan || {}
  const usage = data?.usage || {}
  const planId = plan.plan_id || 'free'
  const meta = PLAN_META[planId] || PLAN_META.free
  const isFree = planId === 'free'
  const isEnterprise = planId === 'enterprise'

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-navy-900">
      <Navbar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="px-4 md:px-6 py-3 border-b border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Billing & Usage</h2>
        </div>

        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 space-y-6">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1,2,3].map((i) => <CardSkeleton key={i} />)}
            </div>
          ) : (
            <>
              {/* Current Plan */}
              <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Current Plan</p>
                    <div className="flex items-center gap-2 mt-1">
                      <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{plan.name || 'Free'}</h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${meta.color}`}>
                        {plan.status === 'active' ? 'Active' : plan.status === 'trialing' ? 'Trial' : plan.status === 'past_due' ? 'Past Due' : plan.status || 'Free'}
                      </span>
                    </div>
                  </div>
                  <div className="w-10 h-10 rounded-lg bg-navy-100 dark:bg-navy-700 flex items-center justify-center text-navy-900 dark:text-amber-400">
                    <CreditCard size={20} />
                  </div>
                </div>

                {isFree && (
                  <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-4 mb-4">
                    <div className="flex items-start gap-3">
                      <Zap size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-300">Free plan limits</p>
                        <p className="text-xs text-amber-700 dark:text-amber-400 mt-0.5">
                          {plan.max_documents} documents &bull; {plan.max_queries_monthly} queries/month
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {plan.status === 'past_due' && (
                  <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-4 mb-4">
                    <p className="text-sm text-red-700 dark:text-red-400">
                      Your payment is past due. Please update your payment method to avoid service interruption.
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap gap-3">
                  {isFree && (
                    <button
                      onClick={handleUpgrade}
                      disabled={actionLoading === 'upgrade'}
                      className="px-5 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 transition-colors flex items-center gap-2"
                    >
                      {actionLoading === 'upgrade' ? (
                        <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Loading...</>
                      ) : (
                        <><ArrowUp size={16} /> Upgrade to Professional</>
                      )}
                    </button>
                  )}
                  {!isFree && !isEnterprise && (
                    <button
                      onClick={handlePortal}
                      disabled={actionLoading === 'portal'}
                      className="px-5 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 transition-colors flex items-center gap-2"
                    >
                      {actionLoading === 'portal' ? (
                        <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Loading...</>
                      ) : (
                        <><CreditCard size={16} /> Manage Billing</>
                      )}
                    </button>
                  )}
                  {isEnterprise && (
                    <button
                      onClick={handlePortal}
                      disabled={actionLoading === 'portal'}
                      className="px-5 py-2 bg-navy-900 dark:bg-amber-400 dark:text-navy-900 text-white rounded-lg text-sm font-medium hover:bg-navy-800 dark:hover:bg-amber-500 disabled:opacity-50 transition-colors flex items-center gap-2"
                    >
                      {actionLoading === 'portal' ? (
                        <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> Loading...</>
                      ) : (
                        <><CreditCard size={16} /> Billing Portal</>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Usage Meter */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Chat Queries</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {usage.queries_used ?? 0}
                    <span className="text-sm font-normal text-gray-400 dark:text-gray-500"> / {plan.max_queries_monthly ?? 50}</span>
                  </p>
                  <div className="mt-2 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-navy-900 dark:bg-amber-400 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, ((usage.queries_used ?? 0) / (plan.max_queries_monthly ?? 50)) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Documents</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {usage.documents_used ?? 0}
                    <span className="text-sm font-normal text-gray-400 dark:text-gray-500"> / {plan.max_documents ?? 5}</span>
                  </p>
                  <div className="mt-2 h-2 bg-gray-100 dark:bg-navy-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-navy-900 dark:bg-amber-400 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, ((usage.documents_used ?? 0) / (plan.max_documents ?? 5)) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-4">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Features Used</p>
                  <div className="space-y-1 mt-1">
                    {Object.entries(usage.feature_usage || {}).map(([feat, count]) => (
                      <div key={feat} className="flex items-center justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400 capitalize">{feat.replace('-', ' ')}</span>
                        <span className="font-medium text-gray-900 dark:text-white">{count}</span>
                      </div>
                    ))}
                    {(!usage.feature_usage || Object.keys(usage.feature_usage).length === 0) && (
                      <p className="text-xs text-gray-400 dark:text-gray-500">No feature usage this month</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Features by Plan */}
              <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Plan Features</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    { id: 'free', name: 'Free', price: '$0', features: ['Chat queries (50/mo)', 'Document uploads (5)', 'Basic search'], current: planId === 'free' },
                    { id: 'pro', name: 'Professional', price: '$29/mo', features: ['Chat queries (10k/mo)', 'Document uploads (100)', 'Clause extraction', 'Contract comparison', 'API access'], current: planId === 'pro' },
                    { id: 'enterprise', name: 'Enterprise', price: '$199/mo', features: ['Unlimited queries', 'Unlimited documents', 'All features', 'SSO & SAML', 'Custom branding', 'Dedicated support'], current: planId === 'enterprise' },
                  ].map((p) => (
                    <div
                      key={p.id}
                      className={`rounded-xl border-2 p-4 ${
                        p.current
                          ? 'border-navy-900 dark:border-amber-400 bg-navy-50 dark:bg-navy-700/30'
                          : 'border-gray-200 dark:border-navy-700'
                      }`}
                    >
                      <h4 className="text-base font-bold text-gray-900 dark:text-white">{p.name}</h4>
                      <p className="text-lg font-bold text-navy-900 dark:text-amber-400 mt-1">{p.price}</p>
                      <ul className="mt-3 space-y-1.5">
                        {p.features.map((f) => (
                          <li key={f} className="text-xs text-gray-600 dark:text-gray-400 flex items-center gap-1.5">
                            <Check size={12} className="text-green-500 flex-shrink-0" />
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Invoices */}
              {invoices.length > 0 && (
                <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 p-6">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Invoice History</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 dark:border-navy-700">
                          <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Date</th>
                          <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Amount</th>
                          <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Status</th>
                          <th className="text-right py-2 font-medium text-gray-500 dark:text-gray-400">Invoice</th>
                        </tr>
                      </thead>
                      <tbody>
                        {invoices.map((inv) => (
                          <tr key={inv.id} className="border-b border-gray-100 dark:border-navy-700/50">
                            <td className="py-2 text-gray-700 dark:text-gray-300">
                              {inv.period_start ? new Date(inv.period_start + 'Z').toLocaleDateString() : '—'}
                            </td>
                            <td className="py-2 text-gray-700 dark:text-gray-300">
                              {inv.currency?.toUpperCase()} {(inv.amount_paid / 100).toFixed(2)}
                            </td>
                            <td className="py-2">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                inv.status === 'paid'
                                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                  : inv.status === 'failed'
                                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                                  : 'bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400'
                              }`}>
                                {inv.status}
                              </span>
                            </td>
                            <td className="py-2 text-right">
                              {inv.invoice_pdf && (
                                <a
                                  href={inv.invoice_pdf}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-xs text-navy-900 dark:text-amber-400 font-medium hover:underline"
                                >
                                  <Download size={12} /> PDF
                                </a>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
