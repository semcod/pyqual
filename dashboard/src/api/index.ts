import { Repository, PyqualSummary, DashboardConfig } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const GITHUB_TOKEN = import.meta.env.VITE_GITHUB_TOKEN;

// Load configuration
export const loadConfig = async (): Promise<DashboardConfig> => {
  try {
    const response = await fetch('/config/repos.json');
    if (!response.ok) {
      throw new Error(`Failed to load config: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error loading config:', error);
    // Return default config for development
    return {
      repositories: [],
      refreshInterval: 60
    };
  }
};

// Fetch repositories from config
export const fetchRepositories = async (): Promise<Repository[]> => {
  const config = await loadConfig();
  
  // Fetch latest run for each repository
  const repositories = await Promise.all(
    config.repositories.map(async (repo) => {
      try {
        const lastRun = await fetchLatestRun(repo);
        return { ...repo, lastRun };
      } catch (error) {
        console.error(`Failed to fetch latest run for ${repo.name}:`, error);
        return repo;
      }
    })
  );

  return repositories;
};

// Fetch latest run from GitHub releases
export const fetchLatestRun = async (repository: Repository): Promise<PyqualSummary | null> => {
  // Try to fetch from GitHub releases first
  try {
    const releasesUrl = `https://api.github.com/repos/${getRepoPath(repository.url)}/releases`;
    const response = await fetch(releasesUrl, {
      headers: GITHUB_TOKEN ? { Authorization: `token ${GITHUB_TOKEN}` } : {}
    });

    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.statusText}`);
    }

    const releases = await response.json();
    const latestRelease = releases.find((r: any) => r.assets && r.assets.length > 0);
    
    if (latestRelease) {
      const summaryAsset = latestRelease.assets.find((a: any) => a.name === 'summary.json');
      if (summaryAsset) {
        const summaryResponse = await fetch(summaryAsset.browser_download_url);
        if (summaryResponse.ok) {
          return await summaryResponse.json();
        }
      }
    }
  } catch (error) {
    console.error('Failed to fetch from GitHub releases:', error);
  }

  // Fallback to local API if available
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects/${repository.id}/latest`);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Failed to fetch from local API:', error);
  }

  return null;
};

// Fetch all runs for a repository
export const fetchRepositoryRuns = async (repoId: string): Promise<PyqualSummary[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/projects/${repoId}/runs`);
    if (!response.ok) {
      throw new Error(`Failed to fetch runs: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching repository runs:', error);
    return [];
  }
};

// Fetch metrics history for a repository
export const fetchMetricsHistory = async (
  repoId: string, 
  metric: string, 
  days: number = 30
): Promise<Array<{ timestamp: string; value: number }>> => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/projects/${repoId}/metrics/${metric}?days=${days}`
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch metrics history: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching metrics history:', error);
    return [];
  }
};

// Helper to extract repo path from URL
const getRepoPath = (url: string): string => {
  const match = url.match(/github\.com\/([^\/]+\/[^\/?]+)/);
  return match ? match[1] : '';
};

// Mock data for development
export const mockRepositories: Repository[] = [
  {
    id: 'pyqual',
    name: 'Pyqual',
    url: 'https://github.com/semcod/pyqual',
    branch: 'main',
    ciUrl: 'https://github.com/semcod/pyqual/actions',
    lastRun: {
      timestamp: '2026-03-31T20:00:00Z',
      commit: 'abc123def456',
      branch: 'main',
      status: 'passed',
      duration_s: 62.114,
      iterations: 1,
      metrics: {
        coverage: 85.5,
        maintainability: 75.2,
        security: 100.0,
        reliability: 92.0
      },
      stages: [
        { name: 'test', duration_s: 10.5, passed: true, skipped: false },
        { name: 'lint', duration_s: 5.2, passed: true, skipped: false },
        { name: 'security', duration_s: 15.3, passed: true, skipped: false },
        { name: 'coverage', duration_s: 8.1, passed: true, skipped: false }
      ],
      gates: [
        { metric: 'coverage', value: 85.5, threshold: 80.0, passed: true },
        { metric: 'maintainability', value: 75.2, threshold: 70.0, passed: true },
        { metric: 'security', value: 100.0, threshold: 90.0, passed: true }
      ]
    }
  },
  {
    id: 'my-project',
    name: 'My Project',
    url: 'https://github.com/myorg/my-project',
    branch: 'main',
    ciUrl: 'https://github.com/myorg/my-project/actions',
    lastRun: {
      timestamp: '2026-03-31T18:30:00Z',
      commit: 'def456abc123',
      branch: 'main',
      status: 'failed',
      duration_s: 45.2,
      iterations: 2,
      metrics: {
        coverage: 72.3,
        maintainability: 68.5,
        security: 95.0,
        reliability: 88.0
      },
      stages: [
        { name: 'test', duration_s: 12.3, passed: true, skipped: false },
        { name: 'lint', duration_s: 6.5, passed: false, skipped: false },
        { name: 'security', duration_s: 18.2, passed: true, skipped: false },
        { name: 'coverage', duration_s: 8.2, passed: false, skipped: false }
      ],
      gates: [
        { metric: 'coverage', value: 72.3, threshold: 80.0, passed: false },
        { metric: 'maintainability', value: 68.5, threshold: 70.0, passed: false },
        { metric: 'security', value: 95.0, threshold: 90.0, passed: true }
      ]
    }
  }
];

// Use mock data in development if no real data is available
export const fetchRepositoriesWithFallback = async (): Promise<Repository[]> => {
  try {
    const repos = await fetchRepositories();
    console.log('Fetched repositories:', repos);
    return repos.length > 0 ? repos : mockRepositories;
  } catch (error) {
    console.warn('Using mock data due to error:', error);
    console.log('Mock repositories:', mockRepositories);
    return mockRepositories;
  }
};
