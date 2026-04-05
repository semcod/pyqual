import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Repository, PyqualSummary } from '../types';
import { ArrowLeftIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import MetricsTrendChart from './MetricsTrendChart';
import StagesChart from './StagesChart';

interface RepositoryDetailProps {
  repositories: Repository[];
}

// Helper component for status badge
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const isPassed = status === 'passed';
  const bgClass = isPassed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
  const Icon = isPassed ? CheckCircleIcon : XCircleIcon;

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${bgClass}`}>
      <Icon className="h-4 w-4 mr-1" />
      {status}
    </span>
  );
};

// Helper component for metric card
const MetricCard: React.FC<{
  name: string;
  value: number | string;
  passed: boolean;
  threshold?: number;
}> = ({ name, value, passed, threshold }) => {
  const Icon = passed ? CheckCircleIcon : XCircleIcon;
  const iconColor = passed ? 'text-green-500' : 'text-red-500';

  return (
    <div className="border rounded-lg p-4">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-gray-500 capitalize">
            {name.replace(/_/g, ' ')}
          </p>
          <p className="text-2xl font-semibold text-gray-900">
            {typeof value === 'number' ? value.toFixed(1) : value}
            {name.includes('coverage') && '%'}
          </p>
        </div>
        <Icon className={`h-5 w-5 ${iconColor}`} />
      </div>
      {threshold !== undefined && (
        <p className="text-xs text-gray-500 mt-1">Threshold: {threshold}</p>
      )}
    </div>
  );
};

// Helper component for run details grid
const RunDetails: React.FC<{ run: PyqualSummary }> = ({ run }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <h2 className="text-lg font-medium text-gray-900 mb-4">Latest Run Details</h2>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div>
        <p className="text-sm font-medium text-gray-500">Commit</p>
        <p className="text-sm text-gray-900 font-mono">{run.commit.slice(0, 8)}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">Branch</p>
        <p className="text-sm text-gray-900">{run.branch}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">Timestamp</p>
        <p className="text-sm text-gray-900">{new Date(run.timestamp).toLocaleString()}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">Duration</p>
        <p className="text-sm text-gray-900">{run.duration_s?.toFixed(2)}s</p>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">Iterations</p>
        <p className="text-sm text-gray-900">{run.iterations}</p>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-500">Python Version</p>
        <p className="text-sm text-gray-900">{run.python_version || 'N/A'}</p>
      </div>
    </div>
  </div>
);

// Helper component for metrics section
const MetricsSection: React.FC<{ run: PyqualSummary }> = ({ run }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <h2 className="text-lg font-medium text-gray-900 mb-4">Quality Metrics</h2>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Object.entries(run.metrics).map(([key, value]) => {
        const gate = run.gates.find(g => g.metric === key);
        return (
          <MetricCard
            key={key}
            name={key}
            value={value}
            passed={gate?.passed ?? true}
            threshold={gate?.threshold}
          />
        );
      })}
    </div>
  </div>
);

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
            <StatusBadge status={latestRun.status} />
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
      {latestRun && <RunDetails run={latestRun} />}

      {/* Metrics */}
      {latestRun && <MetricsSection run={latestRun} />}

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
