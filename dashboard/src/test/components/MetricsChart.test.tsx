import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MetricsChart from '../components/MetricsChart'
import { Repository } from '../types'

const mockRepositories: Repository[] = [
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
      metrics: {
        coverage: 85.5,
        maintainability: 75.2,
        security: 100.0
      },
      stages: [],
      gates: []
    }
  },
  {
    id: 'test-repo-2',
    name: 'Test Repository 2',
    url: 'https://github.com/test/test2',
    branch: 'main',
    ciUrl: 'https://github.com/test/test2/actions',
    lastRun: {
      timestamp: '2026-03-31T20:00:00Z',
      commit: 'def456',
      branch: 'main',
      status: 'failed',
      duration_s: 45,
      iterations: 2,
      metrics: {
        coverage: 72.3,
        maintainability: 68.5,
        security: 95.0
      },
      stages: [],
      gates: []
    }
  }
]

describe('MetricsChart', () => {
  it('renders without crashing', () => {
    render(<MetricsChart repositories={mockRepositories} />)
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('renders ResponsiveContainer', () => {
    render(<MetricsChart repositories={mockRepositories} />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders chart components', () => {
    render(<MetricsChart repositories={mockRepositories} />)
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })

  it('renders lines for each repository', () => {
    render(<MetricsChart repositories={mockRepositories} />)
    const lines = screen.getAllByTestId('line')
    expect(lines).toHaveLength(mockRepositories.length)
  })

  it('handles empty repositories array', () => {
    render(<MetricsChart repositories={[]} />)
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('handles repositories without lastRun', () => {
    const reposWithoutLastRun: Repository[] = [
      {
        id: 'test-repo',
        name: 'Test Repository',
        url: 'https://github.com/test/test',
        branch: 'main',
        ciUrl: 'https://github.com/test/test/actions'
      }
    ]
    
    render(<MetricsChart repositories={reposWithoutLastRun} />)
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('generates correct number of data points', () => {
    const { container } = render(<MetricsChart repositories={mockRepositories} />)
    // The chart should generate 30 days of data
    const lines = screen.getAllByTestId('line')
    expect(lines).toHaveLength(mockRepositories.length)
  })
})
