export interface PyqualMetric {
  metric: string;
  value: number;
  threshold?: number;
  passed: boolean;
}

export interface PyqualStage {
  name: string;
  duration_s: number;
  passed: boolean;
  skipped: boolean;
}

export interface PyqualSummary {
  timestamp: string;
  commit: string;
  branch: string;
  pipeline_id?: string;
  job_id?: string;
  project_id?: string;
  project_name?: string;
  project_url?: string;
  pipeline_url?: string;
  python_version?: string;
  status: 'passed' | 'failed';
  duration_s?: number;
  iterations?: number;
  metrics: Record<string, number>;
  stages: PyqualStage[];
  gates: PyqualMetric[];
}

export interface Repository {
  id: string;
  name: string;
  url: string;
  branch: string;
  ciUrl: string;
  lastRun?: PyqualSummary;
  runs?: PyqualSummary[];
}

export interface DashboardConfig {
  repositories: Repository[];
  refreshInterval?: number; // in seconds
  theme?: 'light' | 'dark';
}

export interface MetricHistory {
  timestamp: string;
  value: number;
  runId: string;
}

export interface MetricTrend {
  metric: string;
  current: number;
  previous: number;
  trend: 'up' | 'down' | 'stable';
  history: MetricHistory[];
}
