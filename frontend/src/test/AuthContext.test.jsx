import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider, useAuth } from '../context/AuthContext'
import React from 'react'

vi.mock('../api', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getMe: vi.fn(),
  getDocuments: vi.fn(),
  getBranding: vi.fn().mockRejectedValue(new Error('no branding')),
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
  },
}))

import { loginUser, getMe } from '../api'

describe('AuthContext', () => {
  function TestComponent() {
    const { user, isAdmin, loading, login, logout } = useAuth()
    if (loading) return <div data-testid="loading">Loading...</div>
    return (
      <div>
        <div data-testid="user">{user ? user.username : 'null'}</div>
        <div data-testid="admin">{isAdmin ? 'yes' : 'no'}</div>
        <button data-testid="login-btn" onClick={() => login('a@b.com', 'Pass1')}>Login</button>
        <button data-testid="logout-btn" onClick={logout}>Logout</button>
      </div>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  function renderWithProviders(ui) {
    return render(
      <MemoryRouter>
        <AuthProvider>
          {ui}
        </AuthProvider>
      </MemoryRouter>
    )
  }

  it('shows no user when not authenticated', async () => {
    renderWithProviders(<TestComponent />)
    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('null')
    })
  })

  it('login sets user', async () => {
    loginUser.mockResolvedValue({
      access_token: 'tok',
      user: { id: 1, username: 'testuser', role: 'lawyer' },
    })
    getMe.mockResolvedValue({ id: 1, username: 'testuser', role: 'lawyer' })

    renderWithProviders(<TestComponent />)

    const user = userEvent.setup()
    await user.click(screen.getByTestId('login-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('testuser')
    })
  })

  it('detects admin role', async () => {
    getMe.mockResolvedValue({ id: 1, username: 'admin', role: 'admin' })
    localStorage.setItem('lexbot_token', 'admin-tok')

    renderWithProviders(<TestComponent />)

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('admin')
    })

    expect(screen.getByTestId('admin').textContent).toBe('yes')
  })
})
