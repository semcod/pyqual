import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Overview from '../components/Overview'
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
      stages: [
        { name: 'test', duration_s: 10.5, passed: true, skipped: false },
        { name: 'lint', duration_s: 5.2, passed: true, skipped: false }
      ],
      gates: [
        { metric: 'coverage', value: 85.5, threshold: 80.0, passed: true }
      ]
    }
  },
  {
    id: 'test-repo-2',
    name: 'Test Repository 2',
    url: 'https://github.com/test/test2',
    branch: 'main',
    ciUrl: 'https://github.com/test/test2/actions',
    lastRun: {
      timestamp: '2026-03-31T18:30:00Z',
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
      stages: [
        { name: 'test', duration_s: 12.3, passed: true, skipped: false },
        { name: 'lint', duration_s: 6.5, passed: false, skipped: false }
      ],
      gates: [
        { metric: 'coverage', value: 72.3, threshold: 80.0, passed: false }
      ]
    }
  }
]

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('Overview', () => {
  const mockOnRepositorySelect = vi.fn()

  beforeEach(() => {
    mockOnRepositorySelect.mockClear()
  })

  it('renders overview page', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('Total Repositories')).toBeInTheDocument()
    expect(screen.getByText('Passing')).toBeInTheDocument()
    expect(screen.getByText('Failing')).toBeInTheDocument()
    expect(screen.getByText('Avg Coverage')).toBeInTheDocument()
  })

  it('displays correct repository counts', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('2')).toBeInTheDocument() // Total repos
    expect(screen.getByText('1')).toBeInTheDocument() // Passing repos
    expect(screen.getByText('1')).toBeInTheDocument() // Failing repos
  })

  it('displays average coverage', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    const avgCoverage = (85.5 + 72.3) / 2
    expect(screen.getByText(`${avgCoverage.toFixed(1)}%`)).toBeInTheDocument()
  })

  it('renders recent runs table', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('Recent Runs')).toBeInTheDocument()
    expect(screen.getByText('Repository')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Coverage')).toBeInTheDocument()
    expect(screen.getByText('Duration')).toBeInTheDocument()
  })

  it('displays repository information correctly', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('Test Repository')).toBeInTheDocument()
    expect(screen.getByText('Test Repository 2')).toBeInTheDocument()
    expect(screen.getByText('main')).toBeInTheDocument()
  })

  it('displays status badges correctly', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('✓ passed')).toBeInTheDocument()
    expect(screen.getByText('✗ failed')).toBeInTheDocument()
  })

  it('calls onRepositorySelect when View Details is clicked', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    const viewDetailsButtons = screen.getAllByText('View Details')
    fireEvent.click(viewDetailsButtons[0])
    
    expect(mockOnRepositorySelect).toHaveBeenCalledWith(mockRepositories[0])
  })

  it('renders MetricsChart component', () => {
    renderWithRouter(
      <Overview 
        repositories={mockRepositories} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('Coverage Trends')).toBeInTheDocument()
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('handles empty repositories array', () => {
    renderWithRouter(
      <Overview 
        repositories={[]} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('Total Repositories')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('displays N/A for repositories without runs', () => {
    const reposWithoutRuns: Repository[] = [
      {
        id: 'test-repo',
        name: 'Test Repository',
        url: 'https://github.com/test/test',
        branch: 'main',
        ciUrl: 'https://github.com/test/test/actions'
      }
    ]
    
    renderWithRouter(
      <Overview 
        repositories={reposWithoutRuns} 
        onRepositorySelect={mockOnRepositorySelect} 
      />
    )
    
    expect(screen.getByText('No runs')).toBeInTheDocument()
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })
})
