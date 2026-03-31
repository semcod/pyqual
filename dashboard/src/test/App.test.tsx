import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

// Mock the API functions
vi.mock('../api', () => ({
  fetchRepositoriesWithFallback: vi.fn().mockResolvedValue([
    {
      id: 'test-repo',
      name: 'Test Repository',
      url: 'https://github.com/test/test',
      branch: 'main',
      ciUrl: 'https://github.com/test/test/actions',
      lastRun: {
        timestamp: '2026-03-31T20:00:00Z',
        commit: 'abc123',
        branch: 'main',
        status: 'passed',
        duration_s: 60,
        iterations: 1,
        metrics: { coverage: 85.5 },
        stages: [],
        gates: []
      }
    }
  ])
}))

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('App', () => {
  it('renders without crashing', async () => {
    renderWithRouter(<App />)
    expect(screen.getByText('Pyqual Dashboard')).toBeInTheDocument()
  })

  it('shows navigation links', () => {
    renderWithRouter(<App />)
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Repositories')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    renderWithRouter(<App />)
    expect(screen.getByText('Loading Pyqual Dashboard...')).toBeInTheDocument()
  })
})
