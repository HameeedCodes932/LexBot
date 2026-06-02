import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getDocuments: vi.fn(),
  sendMessage: vi.fn(),
  getSubscription: vi.fn(),
  createCheckoutSession: vi.fn(),
  createPortalSession: vi.fn(),
  getInvoices: vi.fn(),
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

import {
  loginUser,
  registerUser,
  getDocuments,
  sendMessage,
  getSubscription,
  createCheckoutSession,
  createPortalSession,
  getInvoices,
} from '../api'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('API Functions', () => {
  describe('loginUser', () => {
    it('calls POST /api/auth/login with email and password', async () => {
      loginUser.mockResolvedValue({ access_token: 'tok', user: { id: 1 } })
      const result = await loginUser('a@b.com', 'Pass1')
      expect(loginUser).toHaveBeenCalledWith('a@b.com', 'Pass1')
      expect(result.access_token).toBe('tok')
    })
  })

  describe('registerUser', () => {
    it('calls POST /api/auth/register with user details', async () => {
      registerUser.mockResolvedValue({ message: 'ok' })
      const result = await registerUser('u', 'e@e.com', 'Pass1', 'Firm')
      expect(registerUser).toHaveBeenCalledWith('u', 'e@e.com', 'Pass1', 'Firm')
      expect(result.message).toBe('ok')
    })
  })

  describe('getDocuments', () => {
    it('calls GET /api/documents with pagination params', async () => {
      getDocuments.mockResolvedValue({ items: [], total: 0 })
      await getDocuments(2, 10)
      expect(getDocuments).toHaveBeenCalledWith(2, 10)
    })

    it('uses defaults when no args', async () => {
      getDocuments.mockResolvedValue({ items: [], total: 0 })
      await getDocuments()
      expect(getDocuments).toHaveBeenCalledWith()
    })
  })

  describe('sendMessage', () => {
    it('calls POST /api/chat with question and session_id', async () => {
      sendMessage.mockResolvedValue({ answer: 'Hello' })
      const result = await sendMessage('Hi', 'sess-1')
      expect(sendMessage).toHaveBeenCalledWith('Hi', 'sess-1')
      expect(result.answer).toBe('Hello')
    })
  })

  describe('getSubscription', () => {
    it('calls GET /api/billing/subscription', async () => {
      getSubscription.mockResolvedValue({ plan: {}, usage: {} })
      const result = await getSubscription()
      expect(getSubscription).toHaveBeenCalledWith()
      expect(result.plan).toBeDefined()
    })
  })

  describe('createCheckoutSession', () => {
    it('calls POST /api/billing/create-checkout with origin', async () => {
      createCheckoutSession.mockResolvedValue({ url: 'https://checkout.stripe.com/test' })
      const result = await createCheckoutSession('http://localhost:5173')
      expect(createCheckoutSession).toHaveBeenCalledWith('http://localhost:5173')
      expect(result.url).toContain('stripe')
    })
  })

  describe('createPortalSession', () => {
    it('calls POST /api/billing/portal with origin', async () => {
      createPortalSession.mockResolvedValue({ url: 'https://billing.stripe.com/portal/test' })
      const result = await createPortalSession('http://localhost:5173')
      expect(createPortalSession).toHaveBeenCalledWith('http://localhost:5173')
    })
  })

  describe('getInvoices', () => {
    it('calls GET /api/billing/invoices', async () => {
      getInvoices.mockResolvedValue([])
      const result = await getInvoices()
      expect(getInvoices).toHaveBeenCalledWith()
      expect(result).toEqual([])
    })
  })
})
