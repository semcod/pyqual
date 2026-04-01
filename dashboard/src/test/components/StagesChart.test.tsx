import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import StagesChart from '../../components/StagesChart'
import { PyqualStage } from '../../types'

const mockStages: PyqualStage[] = [
  {
    name: 'test',
    duration_s: 10.5,
    passed: true,
    skipped: false
  },
  {
    name: 'lint',
    duration_s: 5.2,
    passed: true,
    skipped: false
  },
  {
    name: 'security',
    duration_s: 15.3,
    passed: false,
    skipped: false
  },
  {
    name: 'coverage',
    duration_s: 8.1,
    passed: true,
    skipped: true
  }
]

describe('StagesChart', () => {
  it('renders without crashing', () => {
    render(<StagesChart stages={mockStages} />)
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('renders ResponsiveContainer', () => {
    render(<StagesChart stages={mockStages} />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders chart components', () => {
    render(<StagesChart stages={mockStages} />)
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    expect(screen.getByTestId('x-axis')).toBeInTheDocument()
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })

  it('renders a bar for the chart', () => {
    render(<StagesChart stages={mockStages} />)
    expect(screen.getByTestId('bar')).toBeInTheDocument()
  })

  it('handles empty stages array', () => {
    render(<StagesChart stages={[]} />)
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('processes stage data correctly', () => {
    render(<StagesChart stages={mockStages} />)
    // The component should render without errors
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('handles stages with zero duration', () => {
    const stagesWithZero: PyqualStage[] = [
      {
        name: 'quick-stage',
        duration_s: 0,
        passed: true,
        skipped: false
      }
    ]
    
    render(<StagesChart stages={stagesWithZero} />)
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('handles skipped stages', () => {
    render(<StagesChart stages={mockStages} />)
    // Should render without errors even with skipped stages
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })

  it('handles failed stages', () => {
    render(<StagesChart stages={mockStages} />)
    // Should render without errors even with failed stages
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
  })
})
