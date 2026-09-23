import React, { useEffect, useState } from 'react';
import { applicationsApi, explorationsApi } from '../services/api';
import { Application, ExplorationRun } from '../types';
import { Layers, Globe, Compass, AlertTriangle, ArrowRight, Play, RefreshCw } from 'lucide-react';

interface DashboardProps {
  onNavigate: (tab: string, contextId?: number) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [runs, setRuns] = useState<ExplorationRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [appsData, runsData] = await Promise.all([
        applicationsApi.getAll(),
        explorationsApi.getAll()
      ]);
      setApps(appsData);
      setRuns(runsData);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError('Could not connect to FastAPI backend. Ensure the backend server is running on http://127.0.0.1:8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Compute actual aggregated metrics from database records
  const totalApps = apps.length;
  const totalEnvs = apps.reduce((acc, app) => acc + (app.environments?.length || 0), 0);
  const totalPagesDiscovered = runs.reduce((acc, run) => acc + run.pages_discovered, 0);
  const totalErrors = runs.reduce((acc, run) => acc + run.error_count, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Dashboard</h1>
          <p className="text-sm text-gray-400">Real-time metrics from actual Playwright exploration runs and database records.</p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={fetchData}
            className="flex items-center space-x-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => onNavigate('exploration')}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm shadow transition"
          >
            <Play className="h-4 w-4 fill-white" />
            <span>New Exploration</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-3">
          <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-400">Applications</span>
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Layers className="h-5 w-5 text-blue-400" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-white">{loading ? '...' : totalApps}</span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-400">Environments</span>
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Globe className="h-5 w-5 text-purple-400" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-white">{loading ? '...' : totalEnvs}</span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-400">Pages Discovered</span>
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <Compass className="h-5 w-5 text-emerald-400" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-white">{loading ? '...' : totalPagesDiscovered}</span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-400">Total Errors Encountered</span>
            <div className="p-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="h-5 w-5 text-red-400" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-bold text-white">{loading ? '...' : totalErrors}</span>
          </div>
        </div>
      </div>

      {/* Recent Exploration Runs */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Recent Exploration Runs</h2>
          <span className="text-xs text-gray-400">{runs.length} runs recorded</span>
        </div>

        {runs.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-3">
            <Compass className="h-10 w-10 mx-auto text-gray-600" />
            <p className="text-sm">No exploration runs recorded yet in the database.</p>
            <button
              onClick={() => onNavigate('exploration')}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs rounded-lg transition"
            >
              Start your first run
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Run ID</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Pages</th>
                  <th className="px-6 py-3">Actions</th>
                  <th className="px-6 py-3">Errors</th>
                  <th className="px-6 py-3">Started</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-medium text-white">RUN-{String(run.id).padStart(3, '0')}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        run.status === 'completed'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : run.status === 'running'
                          ? 'bg-blue-950 text-blue-400 border border-blue-800 animate-pulse'
                          : run.status === 'failed'
                          ? 'bg-red-950 text-red-400 border border-red-800'
                          : 'bg-gray-800 text-gray-400'
                      }`}>
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">{run.pages_discovered}</td>
                    <td className="px-6 py-4">{run.actions_discovered}</td>
                    <td className="px-6 py-4">
                      {run.error_count > 0 ? (
                        <span className="text-red-400 font-medium">{run.error_count}</span>
                      ) : (
                        <span className="text-gray-500">0</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-gray-400">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => onNavigate('results', run.id)}
                        className="inline-flex items-center space-x-1 text-xs text-emerald-400 hover:text-emerald-300 font-medium"
                      >
                        <span>View Results</span>
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
