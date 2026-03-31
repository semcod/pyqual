import React, { useState } from 'react';
import { Cog6ToothIcon } from '@heroicons/react/24/outline';

const Settings: React.FC = () => {
  const [refreshInterval, setRefreshInterval] = useState(60);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <Cog6ToothIcon className="h-6 w-6 text-gray-400 mr-2" />
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Dashboard Configuration</h2>
        </div>
        
        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Refresh Interval (seconds)
            </label>
            <input
              type="number"
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              min="10"
              max="300"
            />
            <p className="mt-1 text-sm text-gray-500">
              How often to refresh data from repositories
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="light">Light</option>
              <option value="dark">Dark (Coming Soon)</option>
            </select>
          </div>

          <div className="pt-4">
            <button
              type="button"
              className="bg-blue-600 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Repository Configuration</h2>
        </div>
        
        <div className="p-6">
          <p className="text-sm text-gray-600">
            To configure repositories, edit the <code className="bg-gray-100 px-1 py-0.5 rounded">config/repos.json</code> file.
          </p>
          <pre className="mt-4 bg-gray-100 p-4 rounded-md overflow-x-auto text-sm">
{`{
  "repositories": [
    {
      "id": "my-project",
      "name": "My Project",
      "url": "https://github.com/myorg/my-project",
      "branch": "main",
      "ciUrl": "https://github.com/myorg/my-project/actions"
    }
  ]
}`}
          </pre>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">API Configuration</h2>
        </div>
        
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              API URL
            </label>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
              readOnly
            />
            <p className="mt-1 text-sm text-gray-500">
              Set via VITE_API_URL environment variable
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              GitHub Token
            </label>
            <input
              type="password"
              defaultValue="••••••••"
              className="mt-1 block w-full border-gray-300 rounded-md shadow-sm"
              readOnly
            />
            <p className="mt-1 text-sm text-gray-500">
              Set via VITE_GITHUB_TOKEN environment variable for higher rate limits
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
