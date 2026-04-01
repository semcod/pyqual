import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import {
  ChartBarIcon,
  CubeIcon,
  DocumentTextIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';
import { Repository } from './types';
import Overview from './components/Overview';
import RepositoryDetail from './components/RepositoryDetail';
import Settings from './components/Settings';
import { fetchRepositoriesWithFallback, fetchRepositoryRuns } from './api';
import './App.css';

function App() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      setLoading(true);
      const repos = await fetchRepositoriesWithFallback();
      console.log('Loaded repositories:', repos);
      setRepositories(repos);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories');
    } finally {
      setLoading(false);
    }
  };

  const handleRepositorySelect = async (repo: Repository) => {
    if (!repo.runs) {
      try {
        const runs = await fetchRepositoryRuns(repo.id);
        setRepositories(prev => 
          prev.map(r => r.id === repo.id ? { ...r, runs } : r)
        );
      } catch (err) {
        console.error('Failed to load repository runs:', err);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Pyqual Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <button 
            onClick={loadRepositories}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <CubeIcon className="h-8 w-8 text-blue-600" />
                  <span className="ml-2 text-xl font-semibold text-gray-900">Pyqual Dashboard</span>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-1 pt-1 border-b-2 border-blue-500 text-sm font-medium text-gray-900"
                  >
                    <ChartBarIcon className="h-4 w-4 mr-2" />
                    Overview
                  </Link>
                  <Link
                    to="/repositories"
                    className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  >
                    <DocumentTextIcon className="h-4 w-4 mr-2" />
                    Repositories
                  </Link>
                  <Link
                    to="/settings"
                    className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                  >
                    <Cog6ToothIcon className="h-4 w-4 mr-2" />
                    Settings
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route 
              path="/" 
              element={<Overview repositories={repositories} onRepositorySelect={handleRepositorySelect} />} 
            />
            <Route 
              path="/repositories/:repoId" 
              element={<RepositoryDetail repositories={repositories} />} 
            />
            <Route 
              path="/repositories" 
              element={
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {repositories.map(repo => (
                    <Link
                      key={repo.id}
                      to={`/repositories/${repo.id}`}
                      className="block"
                    >
                      <RepositoryCard repository={repo} />
                    </Link>
                  ))}
                </div>
              } 
            />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function RepositoryCard({ repository }: { repository: Repository }) {
  const lastRun = repository.lastRun;
  const statusColor = lastRun?.status === 'passed' ? 'green' : 'red';
  const statusIcon = lastRun?.status === 'passed' ? '✓' : '✗';

  return (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">{repository.name}</h3>
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${statusColor}-100 text-${statusColor}-800`}>
          {statusIcon} {lastRun?.status || 'No runs'}
        </span>
      </div>
      
      {lastRun && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Coverage</span>
            <span className="font-medium">{lastRun.metrics.coverage || 'N/A'}%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Duration</span>
            <span className="font-medium">{lastRun.duration_s?.toFixed(1) || 'N/A'}s</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Last run</span>
            <span className="font-medium">
              {new Date(lastRun.timestamp).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
      
      <div className="mt-4">
        <a 
          href={repository.ciUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 text-sm"
          onClick={e => e.stopPropagation()}
        >
          View CI →
        </a>
      </div>
    </div>
  );
}

export default App;
