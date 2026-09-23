import React, { useEffect, useState } from 'react';
import { applicationsApi } from '../services/api';
import { Application } from '../types';
import { Layers, Plus, ExternalLink, Trash2, Globe, Calendar, AlertCircle } from 'lucide-react';

interface ApplicationsProps {
  onNavigate: (tab: string, contextId?: number) => void;
}

export const Applications: React.FC<ApplicationsProps> = ({ onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Application Modal State
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchApps = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await applicationsApi.getAll();
      setApps(data);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch applications from server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      setSubmitting(true);
      await applicationsApi.create({ name, description });
      setName('');
      setDescription('');
      setShowModal(false);
      fetchApps();
    } catch (err: any) {
      alert('Error creating application: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this application and all related data?')) return;

    try {
      await applicationsApi.delete(id);
      fetchApps();
    } catch (err: any) {
      alert('Error deleting application: ' + err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Applications</h1>
          <p className="text-sm text-gray-400">Manage target web applications and their deployment environments.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm shadow transition"
        >
          <Plus className="h-4 w-4" />
          <span>Register Application</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Applications Grid */}
      {loading ? (
        <div className="p-12 text-center text-gray-400">Loading applications from database...</div>
      ) : apps.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center space-y-4">
          <Layers className="h-12 w-12 text-gray-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No applications registered</h3>
          <p className="text-sm text-gray-400 max-w-sm mx-auto">
            Add your first web application to configure environments and start autonomous crawler exploration.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition"
          >
            Register Application
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {apps.map((app) => (
            <div
              key={app.id}
              onClick={() => onNavigate('app-details', app.id)}
              className="bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl p-5 cursor-pointer transition flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <Layers className="h-5 w-5 text-blue-400" />
                  </div>
                  <button
                    onClick={(e) => handleDelete(app.id, e)}
                    className="text-gray-500 hover:text-red-400 p-1 rounded transition opacity-0 group-hover:opacity-100"
                    title="Delete Application"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <h3 className="text-lg font-bold text-white mt-4 group-hover:text-emerald-400 transition">
                  {app.name}
                </h3>
                <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                  {app.description || 'No description provided.'}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
                <div className="flex items-center space-x-1.5">
                  <Globe className="h-3.5 w-3.5 text-gray-500" />
                  <span>{app.environments?.length || 0} Environments</span>
                </div>
                <div className="flex items-center space-x-1 text-emerald-400 font-medium">
                  <span>Manage</span>
                  <ExternalLink className="h-3 w-3" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for Creating Application */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <h2 className="text-lg font-bold text-white">Register New Application</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                  Application Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. CRM System, E-commerce Store"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  placeholder="Brief summary of application purpose and test coverage"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
                >
                  {submitting ? 'Creating...' : 'Create Application'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
