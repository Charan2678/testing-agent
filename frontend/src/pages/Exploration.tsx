import React, { useState, useEffect } from 'react';
import { applicationsApi, explorationsApi } from '../services/api';
import { Application, Environment } from '../types';
import { Play, Compass, ShieldAlert, Cpu, CheckCircle2, AlertCircle, Globe, Edit3, RotateCcw, ExternalLink } from 'lucide-react';

interface ExplorationProps {
  initialAppId?: number;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const Exploration: React.FC<ExplorationProps> = ({ initialAppId, onNavigate }) => {
  const [apps, setApps] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | ''>(initialAppId || '');
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [selectedEnvId, setSelectedEnvId] = useState<number | ''>('');
  
  // Custom & Editable Target Application URL
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [userEditedUrl, setUserEditedUrl] = useState<boolean>(false);

  const [browser, setBrowser] = useState('Chromium');
  const [maxPages, setMaxPages] = useState<number>(30);
  const [maxDepth, setMaxDepth] = useState<number>(3);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadApps = async () => {
      try {
        const data = await applicationsApi.getAll();
        setApps(data);
        if (data.length > 0) {
          if (!selectedAppId || !data.some(a => a.id === selectedAppId)) {
            setSelectedAppId(data[0].id);
          }
        } else {
          setSelectedAppId('');
        }
      } catch (err: any) {
        console.error(err);
        setError('Failed to load applications.');
      }
    };
    loadApps();
  }, []);

  useEffect(() => {
    if (!selectedAppId) {
      setEnvironments([]);
      setSelectedEnvId('');
      setTargetUrl('');
      setUserEditedUrl(false);
      return;
    }

    const loadEnvs = async () => {
      try {
        const data = await applicationsApi.getEnvironments(Number(selectedAppId));
        setEnvironments(data);
        if (data.length > 0) {
          setSelectedEnvId(data[0].id);
          // Auto pre-populate targetUrl with first environment's base_url unless user manually edited it
          if (!userEditedUrl) {
            setTargetUrl(data[0].base_url);
          }
        } else {
          setSelectedEnvId('');
          if (!userEditedUrl) {
            setTargetUrl('');
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadEnvs();
  }, [selectedAppId]);

  const selectedEnv = environments.find((e) => e.id === Number(selectedEnvId));

  // Sync target URL when environment changes if user hasn't typed an explicit custom URL
  const handleEnvChange = (envId: number) => {
    setSelectedEnvId(envId);
    const env = environments.find((e) => e.id === envId);
    if (env && !userEditedUrl) {
      setTargetUrl(env.base_url);
    }
  };

  const handleUrlChange = (val: string) => {
    setTargetUrl(val);
    setUserEditedUrl(true);
  };

  const handleResetToEnvUrl = () => {
    if (selectedEnv) {
      setTargetUrl(selectedEnv.base_url);
      setUserEditedUrl(false);
    }
  };

  const handleQuickFill = (url: string) => {
    setTargetUrl(url);
    setUserEditedUrl(true);
  };

  // Determine if current target URL is custom (different from selected environment's base URL)
  const isCustomUrl = Boolean(
    targetUrl.trim() &&
    (!selectedEnv || targetUrl.trim() !== selectedEnv.base_url.trim())
  );

  // Resolved final URL that Playwright will crawl
  const finalResolvedUrl = (targetUrl.trim() || selectedEnv?.base_url || '').trim();

  // Validate URL structure (must be http/https with valid hostname)
  const validateUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && Boolean(parsed.hostname);
    } catch {
      return false;
    }
  };

  const handleStartExploration = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!selectedAppId || !selectedEnvId) {
      setError('Please select both an Application and a Target Environment.');
      return;
    }

    if (!finalResolvedUrl) {
      setError('Please enter a Target Application URL.');
      return;
    }

    if (!validateUrl(finalResolvedUrl)) {
      setError(`Invalid URL "${finalResolvedUrl}". URL must use http:// or https:// with a valid hostname.`);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // 1. Create exploration run with the validated target URL (custom URL takes precedence)
      const run = await explorationsApi.create({
        application_id: Number(selectedAppId),
        environment_id: Number(selectedEnvId),
        target_url: finalResolvedUrl,
        max_pages: Number(maxPages),
        max_depth: Number(maxDepth)
      });

      // 2. Trigger asynchronous Playwright crawler start
      await explorationsApi.start(run.id, maxPages, maxDepth);

      // 3. Navigate directly to results screen to watch live exploration
      onNavigate('results', run.id);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to start exploration');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Autonomous Application Exploration</h1>
        <p className="text-sm text-gray-400">
          Launch a real Chromium browser instance to crawl pages, extract interactive DOM elements, and collect evidence from any authorized target URL.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800 rounded-lg text-red-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {apps.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center space-y-4">
          <Compass className="h-10 w-10 text-gray-500 mx-auto" />
          <h3 className="text-base font-semibold text-white">No applications available</h3>
          <p className="text-sm text-gray-400">
            Please register an application and configure at least one environment URL before starting an exploration.
          </p>
          <button
            onClick={() => onNavigate('applications')}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition"
          >
            Go to Applications
          </button>
        </div>
      ) : (
        <form onSubmit={handleStartExploration} className="bg-gray-900 border border-gray-800 rounded-xl p-6 sm:p-8 space-y-6">
          {/* Application Selection */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
              Select Application *
            </label>
            <select
              value={selectedAppId}
              onChange={(e) => setSelectedAppId(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            >
              {apps.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.name}
                </option>
              ))}
            </select>
          </div>

          {/* Environment Selection */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
              Select Baseline Environment *
            </label>
            {environments.length === 0 ? (
              <div className="p-3 bg-gray-800 border border-gray-700 rounded-lg text-xs text-amber-400 flex items-center justify-between">
                <span>No environment configured for this application.</span>
                <button
                  type="button"
                  onClick={() => onNavigate('app-details', Number(selectedAppId))}
                  className="underline font-semibold"
                >
                  Add Environment
                </button>
              </div>
            ) : (
              <select
                value={selectedEnvId}
                onChange={(e) => handleEnvChange(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              >
                {environments.map((env) => (
                  <option key={env.id} value={env.id}>
                    {env.name} — {env.base_url} ({env.environment_type})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* EDITABLE Target Application URL Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="target-app-url-input" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Target Application URL *
              </label>
              <div className="flex items-center space-x-2">
                {isCustomUrl ? (
                  <span className="text-[11px] px-2 py-0.5 font-medium tracking-wide bg-indigo-950 text-indigo-300 border border-indigo-700 rounded-full flex items-center space-x-1">
                    <Edit3 className="h-3 w-3" />
                    <span>Custom Target URL Override</span>
                  </span>
                ) : (
                  <span className="text-[11px] px-2 py-0.5 font-medium tracking-wide bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-full flex items-center space-x-1">
                    <Globe className="h-3 w-3" />
                    <span>Predefined Environment URL</span>
                  </span>
                )}
                {isCustomUrl && selectedEnv && (
                  <button
                    type="button"
                    onClick={handleResetToEnvUrl}
                    className="text-[11px] text-gray-400 hover:text-white flex items-center space-x-1 px-1.5 py-0.5 hover:bg-gray-800 rounded transition"
                    title="Reset to selected environment's base URL"
                  >
                    <RotateCcw className="h-3 w-3" />
                    <span>Reset</span>
                  </button>
                )}
              </div>
            </div>

            <div className="relative">
              <input
                id="target-app-url-input"
                type="text"
                value={targetUrl}
                onChange={(e) => handleUrlChange(e.target.value)}
                placeholder="e.g. http://127.0.0.1:3000 or https://example.com"
                className={`w-full bg-gray-950 border ${
                  isCustomUrl ? 'border-indigo-500 ring-1 ring-indigo-500/30' : 'border-gray-700'
                } rounded-lg px-3.5 py-2.5 font-mono text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition`}
              />
            </div>

            {/* Quick-fill Example Pills */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs text-gray-400">
              <span className="text-gray-500">Quick Fill:</span>
              <button
                type="button"
                onClick={() => handleQuickFill('http://127.0.0.1:3000')}
                className="px-2 py-0.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[11px] font-mono transition"
              >
                http://127.0.0.1:3000
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill('http://localhost:3000')}
                className="px-2 py-0.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[11px] font-mono transition"
              >
                http://localhost:3000
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill('https://example.com')}
                className="px-2 py-0.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[11px] font-mono transition"
              >
                https://example.com
              </button>
            </div>
          </div>

          {/* Final Resolved Target URL Preview Card */}
          <div className="p-3.5 bg-gray-950 border border-gray-800 rounded-lg space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span className="font-semibold uppercase tracking-wider text-gray-300">Resolved Entrypoint for Playwright:</span>
              <span className={`text-[11px] font-mono font-medium ${isCustomUrl ? 'text-indigo-400' : 'text-emerald-400'}`}>
                {isCustomUrl ? 'CUSTOM URL PRECEDENCE' : 'ENVIRONMENT DEFAULT'}
              </span>
            </div>
            <div className="font-mono text-sm text-emerald-400 break-all flex items-center space-x-2">
              <Globe className="h-4 w-4 text-emerald-500 flex-shrink-0" />
              <span>{finalResolvedUrl || '(No URL specified)'}</span>
            </div>
            <p className="text-[11px] text-gray-500">
              Playwright will initiate the crawl at this exact URL. Internal links matching this origin will be cataloged.
            </p>
          </div>

          {/* Browser & Limits Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
                Browser Engine
              </label>
              <select
                value={browser}
                onChange={(e) => setBrowser(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="Chromium">Chromium (Google Chrome)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
                Max Pages Limit
              </label>
              <input
                type="number"
                min={1}
                max={100}
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-4 bg-gray-950/70 border border-gray-800 rounded-lg flex items-start space-x-3 text-xs text-gray-400">
            <ShieldAlert className="h-5 w-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-gray-200">Phase 1 Non-Destructive Safety Policy:</span> The explorer
              crawls internal pages, extracts elements, records console logs, captures network requests, and takes screenshots.
              Destructive actions (Delete, Payment, Purchase, Password/Account Changes, Logout) are strictly inventoried but never triggered.
            </div>
          </div>

          {/* Start Button */}
          <button
            type="submit"
            disabled={loading || !selectedEnvId || !finalResolvedUrl}
            className="w-full py-3.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-lg text-base shadow-lg transition flex items-center justify-center space-x-2"
          >
            <Play className={`h-5 w-5 fill-white ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Initializing Playwright Browser...' : 'Start Exploration'}</span>
          </button>
        </form>
      )}
    </div>
  );
};
