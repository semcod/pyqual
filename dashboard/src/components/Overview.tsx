import React from 'react';
import { Repository } from '../types';
import { 
  ChartBarIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';
import MetricsChart from './MetricsChart';

interface OverviewProps {
  repositories: Repository[];
  onRepositorySelect: (repo: Repository) => void;
}

const Overview: React.FC<OverviewProps> = ({ repositories, onRepositorySelect }) => {
  const totalRepos = repositories.length;
  const passingRepos = repositories.filter(r => r.lastRun?.status === 'passed').length;
  const failingRepos = totalRepos - passingRepos;
  const avgCoverage = repositories.reduce((acc, r) => 
    acc + (r.lastRun?.metrics.coverage || 0), 0) / totalRepos || 0;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ChartBarIcon className="h-8 w-8 text-gray-400" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Repositories</p>
              <p className="text-2xl font-semibold text-gray-900">{totalRepos}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircleIcon className="h-8 w-8 text-green-500" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Passing</p>
              <p className="text-2xl font-semibold text-green-600">{passingRepos}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-8 w-8 text-red-500" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Failing</p>
              <p className="text-2xl font-semibold text-red-600">{failingRepos}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <ClockIcon className="h-8 w-8 text-blue-500" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Coverage</p>
              <p className="text-2xl font-semibold text-gray-900">{avgCoverage.toFixed(1)}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Runs Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Recent Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Repository
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Coverage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Run
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {repositories.map((repo) => (
                <tr key={repo.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{repo.name}</div>
                    <div className="text-sm text-gray-500">{repo.branch}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {repo.lastRun ? (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        repo.lastRun.status === 'passed' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {repo.lastRun.status === 'passed' ? '✓' : '✗'} {repo.lastRun.status}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">No runs</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {repo.lastRun?.metrics.coverage ? 
                      `${repo.lastRun.metrics.coverage.toFixed(1)}%` : 
                      'N/A'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {repo.lastRun?.duration_s ? 
                      `${repo.lastRun.duration_s.toFixed(1)}s` : 
                      'N/A'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {repo.lastRun ? 
                      new Date(repo.lastRun.timestamp).toLocaleString() : 
                      'Never'
                    }
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => onRepositorySelect(repo)}
                      className="text-blue-600 hover:text-blue-900 mr-3"
                    >
                      View Details
                    </button>
                    <a
                      href={repo.ciUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-600 hover:text-gray-900"
                    >
                      CI
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Metrics Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Coverage Trends</h2>
        <MetricsChart repositories={repositories} />
      </div>
    </div>
  );
};

export default Overview;
