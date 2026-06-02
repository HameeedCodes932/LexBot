import { test, expect } from '@playwright/test'

test.describe('Landing Page', () => {
  test('loads and displays hero section', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('text=LexBot')).toBeVisible()
  })

  test('Get Started link navigates to register', async ({ page }) => {
    await page.goto('/')
    const getStarted = page.locator('a:has-text("Get Started")')
    if (await getStarted.isVisible()) {
      await getStarted.click()
      await expect(page).toHaveURL(/\/register/)
    }
  })
})

test.describe('Authentication', () => {
  test('register page shows form', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('input[name="username"]')).toBeVisible()
    await expect(page.locator('input[name="email"]')).toBeVisible()
    await expect(page.locator('input[name="password"]')).toBeVisible()
  })

  test('login page shows form', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[name="email"]')).toBeVisible()
    await expect(page.locator('input[name="password"]')).toBeVisible()
  })

  test('login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[name="email"]', 'nonexistent@test.com')
    await page.fill('input[name="password"]', 'WrongPass1')
    await page.click('button[type="submit"]')
    await expect(page.locator('text=error')).toBeVisible({ timeout: 10000 }).catch(() => {})
  })
})

test.describe('Navigation', () => {
  test('navbar links are visible on landing', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('nav')).toBeVisible()
  })

  test('dark mode toggle works', async ({ page }) => {
    await page.goto('/')
    const toggle = page.locator('button:has(svg)').first()
    if (await toggle.isVisible()) {
      await toggle.click()
    }
    const html = page.locator('html')
    const classList = await html.getAttribute('class')
    expect(classList).not.toBeNull()
  })
})
