import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '../context/ThemeContext'
import RiskBadge from '../components/RiskBadge'
import SourceCard from '../components/SourceCard'
import ProtectedRoute from '../components/ProtectedRoute'
import React from 'react'

// Mock the api module
vi.mock('../api', () => ({
  getMe: vi.fn().mockRejectedValue(new Error('No token')),
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

const mockUseAuth = vi.fn()
vi.mock('../context/AuthContext', () => ({
  useAuth: (...args) => mockUseAuth(...args),
  AuthProvider: ({ children }) => <>{children}</>,
}))

describe('RiskBadge', () => {
  it('renders the term text', () => {
    render(<RiskBadge term="Unlimited Liability" />)
    expect(screen.getByText('Unlimited Liability')).toBeInTheDocument()
  })

  it('has amber styling classes', () => {
    const { container } = render(<RiskBadge term="Auto-Renewal" />)
    const span = container.firstChild
    expect(span.className).toContain('amber')
  })
})

describe('SourceCard', () => {
  it('renders document name and chunk index', () => {
    render(<SourceCard document="contract.pdf" chunk_index={3} preview="This is a preview text" />)
    expect(screen.getByText(/contract.pdf/)).toBeInTheDocument()
    expect(screen.getByText(/Chunk 3/)).toBeInTheDocument()
  })

  it('renders preview text', () => {
    render(<SourceCard document="doc.pdf" chunk_index={1} preview="Sample preview content" />)
    expect(screen.getByText('Sample preview content')).toBeInTheDocument()
  })
})

describe('ProtectedRoute', () => {
  it('shows spinner while loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, isAdmin: false })
    const { container } = render(
      <MemoryRouter>
        <ProtectedRoute>
          <div data-testid="protected-content">Secret</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: { id: 1, username: 'test' },
      loading: false,
      isAdmin: false,
    })
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div data-testid="protected-content">Secret</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
  })
})
