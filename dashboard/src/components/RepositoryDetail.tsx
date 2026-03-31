import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Repository, PyqualSummary } from '../types';
import { ArrowLeftIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import MetricsTrendChart from './MetricsTrendChart';
import StagesChart from './StagesChart';

interface RepositoryDetailProps {
  repositories: Repository[];
}

const RepositoryDetail: React.FC<RepositoryDetailProps> = ({ repositories }) => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const [repository, setRepository] = useState<Repository | null>(null);
  const [runs, setRuns] = useState<PyqualSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const repo = repositories.find(r => r.id === repoId);
    if (repo) {
      setRepository(repo);
      // In a real implementation, fetch historical runs
      setRuns(repo.runs || [repo.lastRun].filter(Boolean) as PyqualSummary[]);
    }
    setLoading(false);
  }, [repoId, repositories]);

  if (loading) {
    return <div className="flex justify-center items-center h-64">Loading...</div>;
  }

  if (!repository) {
    return (
      <div className="text-center">
        <p className="text-gray-500">Repository not found</p>
        <Link to="/" className="text-blue-600 hover:text-blue-800">
          Go back to overview
        </Link>
      </div>
    );
  }

  const latestRun = repository.lastRun;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={() => navigate('/')}
            className="mr-4 p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{repository.name}</h1>
            <p className="text-gray-500">{repository.url}</p>
          </div>
        </div>
        {latestRun && (
          <div className="flex items-center space-x-4">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              latestRun.status === 'passed' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {latestRun.status === 'passed' ? (
                <CheckCircleIcon className="h-4 w-4 mr-1" />
              ) : (
                <XCircleIcon className="h-4 w-4 mr-1" />
              )}
              {latestRun.status}
            </span>
            <a
              href={repository.ciUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800"
            >
              View CI
            </a>
          </div>
        )}
      </div>

      {/* Latest Run Summary */}
      {latestRun && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Latest Run Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm font-medium text-gray-500">Commit</p>
              <p className="text-sm text-gray-900 font-mono">{latestRun.commit.slice(0, 8)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Branch</p>
              <p className="text-sm text-gray-900">{latestRun.branch}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Timestamp</p>
              <p className="text-sm text-gray-900">
                {new Date(latestRun.timestamp).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Duration</p>
              <p className="text-sm text-gray-900">{latestRun.duration_s?.toFixed(2)}s</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Iterations</p>
              <p className="text-sm text-gray-900">{latestRun.iterations}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Python Version</p>
              <p className="text-sm text-gray-900">{latestRun.python_version || 'N/A'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Metrics */}
      {latestRun && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Quality Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(latestRun.metrics).map(([key, value]) => {
              const gate = latestRun.gates.find(g => g.metric === key);
              const passed = gate?.passed ?? true;
              return (
                <div key={key} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm font-medium text-gray-500 capitalize">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-2xl font-semibold text-gray-900">
                        {typeof value === 'number' ? value.toFixed(1) : value}
                        {key.includes('coverage') && '%'}
                      </p>
                    </div>
                    {passed ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                  {gate?.threshold && (
                    <p className="text-xs text-gray-500 mt-1">
                      Threshold: {gate.threshold}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stages */}
      {latestRun && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Stage Performance</h2>
          <StagesChart stages={latestRun.stages} />
        </div>
      )}

      {/* Metrics Trend */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Historical Trends</h2>
        <MetricsTrendChart runs={runs} />
      </div>
    </div>
  );
};

export default RepositoryDetail;
