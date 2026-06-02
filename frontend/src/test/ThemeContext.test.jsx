import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from '../context/ThemeContext'
import React from 'react'

describe('ThemeContext', () => {
  function TestComponent() {
    const { isDark, toggle } = useTheme()
    return (
      <div>
        <div data-testid="theme">{isDark ? 'dark' : 'light'}</div>
        <button data-testid="toggle" onClick={toggle}>Toggle</button>
      </div>
    )
  }

  function renderWithProvider() {
    return render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )
  }

  it('defaults to light mode', () => {
    localStorage.removeItem('lexbot_theme')
    renderWithProvider()
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('toggles between light and dark', async () => {
    localStorage.removeItem('lexbot_theme')
    renderWithProvider()
    const btn = screen.getByTestId('toggle')

    expect(screen.getByTestId('theme').textContent).toBe('light')
    await userEvent.click(btn)
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    await userEvent.click(btn)
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('reads persisted theme from localStorage', () => {
    localStorage.setItem('lexbot_theme', 'dark')
    renderWithProvider()
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    localStorage.removeItem('lexbot_theme')
  })

  it('applies/removes dark class on document element', () => {
    localStorage.removeItem('lexbot_theme')
    renderWithProvider()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
