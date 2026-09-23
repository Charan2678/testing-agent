import React, { useEffect, useState } from 'react';
import { applicationsApi } from '../services/api';
import { Application, Environment, DiscoveredPage } from '../types';
import { ArrowLeft, Globe, Plus, Play, Compass, Layers, ShieldCheck } from 'lucide-react';

interface ApplicationDetailsProps {
  appId: number;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const ApplicationDetails: React.FC<ApplicationDetailsProps> = ({ appId, onNavigate }) => {
  const [app, setApp] = useState<Application | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [pages, setPages] = useState<DiscoveredPage[]>([]);
  const [loading, setLoading] = useState(true);

  // New Environment Modal
  const [showEnvModal, setShowEnvModal] = useState(false);
  const [envName, setEnvName] = useState('Development');
  const [baseUrl, setBaseUrl] = useState('http://localhost:3000');
  const [envType, setEnvType] = useState('development');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [appData, envsData, pagesData] = await Promise.all([
        applicationsApi.getById(appId),
        applicationsApi.getEnvironments(appId),
        applicationsApi.getPages(appId)
      ]);
      setApp(appData);
      setEnvs(envsData);
      setPages(pagesData);
    } catch (err: any) {
      console.error(err);
      alert('Failed to load application details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [appId]);

  const handleCreateEnv = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await applicationsApi.createEnvironment(appId, {
        name: envName,
        base_url: baseUrl,
        environment_type: envType
      });
      setShowEnvModal(false);
      loadData();
    } catch (err: any) {
      alert('Failed to create environment: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-gray-400">Loading application details...</div>;
  }

  if (!app) {
    return (
      <div className="text-center p-12 text-gray-400 space-y-4">
        <p>Application not found.</p>
        <button onClick={() => onNavigate('applications')} className="text-emerald-400 font-medium">
          Return to Applications
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button and title */}
      <div>
        <button
          onClick={() => onNavigate('applications')}
          className="inline-flex items-center space-x-1.5 text-xs text-gray-400 hover:text-white transition mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Applications</span>
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{app.name}</h1>
            <p className="text-sm text-gray-400">{app.description || 'No description provided.'}</p>
          </div>
          <button
            onClick={() => onNavigate('exploration', app.id)}
            className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm shadow transition"
          >
            <Play className="h-4 w-4 fill-white" />
            <span>Launch Exploration</span>
          </button>
        </div>
      </div>

      {/* Environments Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Target Environments</h2>
            <p className="text-xs text-gray-400">Configure deployment URLs (Dev, QA, Staging, UAT)</p>
          </div>
          <button
            onClick={() => setShowEnvModal(true)}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium transition"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Environment</span>
          </button>
        </div>

        {envs.length === 0 ? (
          <div className="py-8 text-center text-gray-500 text-sm">
            No environments configured. Add an environment with a base URL to start testing.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {envs.map((env) => (
              <div key={env.id} className="bg-gray-950 border border-gray-800 rounded-lg p-4 flex justify-between items-center">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-white text-sm">{env.name}</span>
                    <span className="px-2 py-0.5 text-[10px] uppercase font-bold bg-blue-950 text-blue-400 border border-blue-800 rounded">
                      {env.environment_type}
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1 font-mono">{env.base_url}</div>
                </div>
                <button
                  onClick={() => onNavigate('exploration', app.id)}
                  className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 rounded text-xs font-medium flex items-center space-x-1"
                >
                  <Play className="h-3 w-3 fill-emerald-400" />
                  <span>Explore</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Discovered Pages Map */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Discovered Application Map</h2>
            <p className="text-xs text-gray-400">Actual pages discovered by autonomous exploration</p>
          </div>
          <span className="text-xs font-medium px-2 py-1 bg-gray-800 text-gray-300 rounded">
            {pages.length} Pages
          </span>
        </div>

        {pages.length === 0 ? (
          <div className="p-12 text-center text-gray-500 space-y-2">
            <Compass className="h-8 w-8 mx-auto text-gray-600" />
            <p className="text-sm">No pages discovered yet.</p>
            <p className="text-xs text-gray-400">Run an exploration to crawl and map out this application.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Page URL</th>
                  <th className="px-6 py-3">Title</th>
                  <th className="px-6 py-3">Elements</th>
                  <th className="px-6 py-3">First Seen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {pages.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                        p.status_code && p.status_code < 400
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-red-950 text-red-400 border border-red-800'
                      }`}>
                        {p.status_code || 200}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-200">{p.url}</td>
                    <td className="px-6 py-4 text-white font-medium">{p.title || 'Untitled'}</td>
                    <td className="px-6 py-4">{p.elements_count} controls</td>
                    <td className="px-6 py-4 text-xs text-gray-400">
                      {new Date(p.first_seen_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Environment Modal */}
      {showEnvModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <h2 className="text-lg font-bold text-white">Add Target Environment</h2>
            <form onSubmit={handleCreateEnv} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                  Environment Name *
                </label>
                <input
                  type="text"
                  required
                  value={envName}
                  onChange={(e) => setEnvName(e.target.value)}
                  placeholder="e.g. Local Dev, QA Cluster"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                  Base URL *
                </label>
                <input
                  type="url"
                  required
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="http://localhost:3000"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                  Environment Type
                </label>
                <select
                  value={envType}
                  onChange={(e) => setEnvType(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="development">Development</option>
                  <option value="qa">QA</option>
                  <option value="staging">Staging</option>
                  <option value="uat">UAT</option>
                  <option value="production">Production (Controlled)</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEnvModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
                >
                  {submitting ? 'Adding...' : 'Save Environment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
