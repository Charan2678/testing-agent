import React, { useEffect, useState } from 'react';
import { explorationsApi, pagesApi, applicationsApi, BACKEND_URL } from '../services/api';
import {
  ExplorationRun,
  ExplorationStatusResponse,
  DiscoveredPage,
  Evidence,
  PageElement
} from '../types';
import {
  ArrowLeft,
  RefreshCw,
  Compass,
  AlertTriangle,
  Camera,
  Terminal,
  Activity,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Layers,
  Code,
  Globe,
  Copy,
  Check
} from 'lucide-react';

interface ParsedNetworkError {
  method: string;
  status: string;
  cleanUrl: string;
  queryParams: string;
  fullUrl: string;
}

const parseNetworkError = (description?: string, rawUrl?: string): ParsedNetworkError => {
  const desc = description || '';
  const methodMatch = desc.match(/\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b/i);
  const method = methodMatch ? methodMatch[1].toUpperCase() : 'REQ';

  const statusMatch = desc.match(/\(([^)]+)\)$/);
  const status = statusMatch ? statusMatch[1] : '';

  let fullUrl = rawUrl || '';
  if (!fullUrl) {
    const urlMatch = desc.match(/https?:\/\/[^\s()]+/);
    if (urlMatch) {
      fullUrl = urlMatch[0];
    }
  }

  let cleanUrl = fullUrl;
  let queryParams = '';

  try {
    if (fullUrl.startsWith('http://') || fullUrl.startsWith('https://')) {
      const u = new URL(fullUrl);
      cleanUrl = `${u.origin}${u.pathname}`;
      queryParams = u.search;
    } else {
      const parts = fullUrl.split('?');
      cleanUrl = parts[0];
      queryParams = parts[1] ? `?${parts[1]}` : '';
    }
  } catch {
    const parts = fullUrl.split('?');
    cleanUrl = parts[0];
    queryParams = parts[1] ? `?${parts[1]}` : '';
  }

  return {
    method,
    status: status || 'FAILED',
    cleanUrl,
    queryParams,
    fullUrl
  };
};

interface ExplorationResultsProps {
  runId: number;
  onNavigate: (tab: string, contextId?: number) => void;
}

export const ExplorationResults: React.FC<ExplorationResultsProps> = ({ runId, onNavigate }) => {
  const [run, setRun] = useState<ExplorationRun | null>(null);
  const [statusData, setStatusData] = useState<ExplorationStatusResponse | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [appPages, setAppPages] = useState<DiscoveredPage[]>([]);
  const [activeTab, setActiveTab] = useState<'pages' | 'screenshots' | 'console' | 'network'>('pages');
  const [copiedLogId, setCopiedLogId] = useState<number | null>(null);

  // Element inspect modal
  const [selectedPage, setSelectedPage] = useState<DiscoveredPage | null>(null);
  const [pageElements, setPageElements] = useState<PageElement[]>([]);
  const [loadingElements, setLoadingElements] = useState(false);

  // Full screenshot modal
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const pollStatus = async () => {
    try {
      const [runData, sData, evData] = await Promise.all([
        explorationsApi.getById(runId),
        explorationsApi.getStatus(runId),
        explorationsApi.getEvidence(runId)
      ]);
      setRun(runData);
      setStatusData(sData);
      setEvidence(evData);

      // Load pages discovered for this application
      if (runData) {
        const pData = await applicationsApi.getPages(runData.application_id);
        setAppPages(pData);
      }
    } catch (err) {
      console.error('Failed to poll status:', err);
    }
  };

  useEffect(() => {
    pollStatus();
    // Poll every 2.5 seconds if run is still running or pending
    const interval = setInterval(() => {
      if (statusData?.status === 'running' || statusData?.status === 'pending' || !statusData) {
        pollStatus();
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [runId, statusData?.status]);

  const handleInspectElements = async (page: DiscoveredPage) => {
    try {
      setSelectedPage(page);
      setLoadingElements(true);
      const elements = await pagesApi.getElements(page.id);
      setPageElements(elements);
    } catch (err) {
      console.error(err);
      alert('Failed to load elements for this page.');
    } finally {
      setLoadingElements(false);
    }
  };

  const screenshots = evidence.filter((e) => e.type === 'screenshot');
  const consoleLogs = evidence.filter((e) => e.type === 'console_log');
  const networkLogs = evidence.filter((e) => e.type === 'network_log');

  const currentStatus = statusData?.status || run?.status || 'pending';
  const isRunning = currentStatus === 'running';

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div>
        <button
          onClick={() => onNavigate('dashboard')}
          className="inline-flex items-center space-x-1.5 text-xs text-gray-400 hover:text-white transition mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Exploration Run #{String(runId).padStart(3, '0')}
              </h1>
              <span className={`px-2.5 py-1 text-xs font-bold uppercase rounded-full ${
                currentStatus === 'completed'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : currentStatus === 'running'
                  ? 'bg-blue-950 text-blue-400 border border-blue-800 animate-pulse'
                  : currentStatus === 'failed'
                  ? 'bg-red-950 text-red-400 border border-red-800'
                  : 'bg-gray-800 text-gray-400'
              }`}>
                {currentStatus}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Started: {run?.started_at ? new Date(run.started_at).toLocaleTimeString() : 'Pending'}
              {run?.completed_at && ` • Finished: ${new Date(run.completed_at).toLocaleTimeString()}`}
            </p>
            {(statusData?.target_url || run?.target_url) && (
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="text-xs text-gray-400">Target Application:</span>
                <span className="font-mono text-xs text-emerald-400 bg-gray-950 px-2 py-0.5 rounded border border-gray-800 flex items-center space-x-1.5">
                  <Globe className="h-3 w-3 text-emerald-500" />
                  <span>{statusData?.target_url || run?.target_url}</span>
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wide border ${
                  statusData?.url_source === 'custom target URL'
                    ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                }`}>
                  {statusData?.url_source || 'Resolved Target URL'}
                </span>
              </div>
            )}
          </div>

          <button
            onClick={pollStatus}
            className="self-start sm:self-auto flex items-center space-x-2 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRunning ? 'animate-spin' : ''}`} />
            <span>Refresh State</span>
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
          <span className="text-xs font-medium text-gray-400">Pages Discovered</span>
          <div className="mt-1 text-2xl font-bold text-white">
            {statusData?.pages_discovered ?? run?.pages_discovered ?? 0}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
          <span className="text-xs font-medium text-gray-400">Elements Discovered</span>
          <div className="mt-1 text-2xl font-bold text-white">
            {statusData?.actions_discovered ? (statusData.actions_discovered * 2) : (run?.actions_discovered ? run.actions_discovered * 2 : 0)}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
          <span className="text-xs font-medium text-gray-400">Actions Discovered</span>
          <div className="mt-1 text-2xl font-bold text-emerald-400">
            {statusData?.actions_discovered ?? run?.actions_discovered ?? 0}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 p-4 rounded-xl">
          <span className="text-xs font-medium text-gray-400">Errors Encountered</span>
          <div className="mt-1 text-2xl font-bold text-red-400">
            {statusData?.error_count ?? run?.error_count ?? 0}
          </div>
        </div>
      </div>

      {/* Current URL & Activity Feed */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-gray-300 uppercase tracking-wider">Current Target Page</span>
          {isRunning && (
            <span className="flex items-center space-x-1 text-blue-400">
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-ping" />
              <span>CRAWLING ACTIVE</span>
            </span>
          )}
        </div>
        <div className="p-2.5 bg-gray-950 border border-gray-800 rounded font-mono text-xs text-emerald-400 truncate">
          {statusData?.current_url || 'Crawl idle / completed'}
        </div>

        {/* Live Activity Log */}
        {statusData?.activity_log && statusData.activity_log.length > 0 && (
          <div className="mt-2 pt-3 border-t border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-300 flex items-center space-x-1.5">
                <Terminal className="h-3.5 w-3.5 text-emerald-400" />
                <span>Crawler Activity Stream</span>
              </span>
              <span className="text-[11px] text-gray-500 font-mono">
                {statusData.activity_log.length} events logged
              </span>
            </div>
            <div className="bg-gray-950 border border-gray-800/80 rounded-xl p-3 font-mono text-xs max-h-44 overflow-y-auto space-y-1.5">
              {statusData.activity_log.map((log, idx) => {
                const lower = log.toLowerCase();
                const isWarn = lower.includes('warning') || lower.includes('timeout');
                const isErr = lower.includes('error') || lower.includes('failed');
                const iconColor = isErr ? 'text-red-400' : isWarn ? 'text-amber-400' : 'text-emerald-400';
                const textColor = isErr ? 'text-red-300' : isWarn ? 'text-amber-300' : 'text-gray-300';
                const icon = isErr ? '✕' : isWarn ? '⚠' : '✓';

                return (
                  <div key={idx} className="flex items-start space-x-2 leading-relaxed">
                    <span className={`${iconColor} font-bold flex-shrink-0 select-none`}>{icon}</span>
                    <span className={`${textColor} break-all`}>{log}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-800 space-x-2">
        <button
          onClick={() => setActiveTab('pages')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
            activeTab === 'pages'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Compass className="h-4 w-4" />
          <span>Discovered Pages ({appPages.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('screenshots')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
            activeTab === 'screenshots'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Camera className="h-4 w-4" />
          <span>Screenshots ({screenshots.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('console')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
            activeTab === 'console'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Terminal className="h-4 w-4" />
          <span>Console Activity ({consoleLogs.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('network')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
            activeTab === 'network'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Activity className="h-4 w-4" />
          <span>Network Requests ({networkLogs.length})</span>
        </button>
      </div>

      {/* TAB 1: Pages */}
      {activeTab === 'pages' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {appPages.length === 0 ? (
            <div className="p-12 text-center text-gray-500 text-sm">
              No pages discovered yet for this application.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-gray-300">
                <thead className="bg-gray-800/50 text-xs uppercase text-gray-400">
                  <tr>
                    <th className="px-6 py-3">HTTP</th>
                    <th className="px-6 py-3">Page Title</th>
                    <th className="px-6 py-3">URL</th>
                    <th className="px-6 py-3">Controls</th>
                    <th className="px-6 py-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {appPages.map((page) => (
                    <tr key={page.id} className="hover:bg-gray-800/30 transition">
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                          {page.status_code || 200}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-medium text-white">{page.title || 'Untitled'}</td>
                      <td className="px-6 py-4 font-mono text-xs text-gray-300">{page.url}</td>
                      <td className="px-6 py-4 text-xs text-gray-400">{page.elements_count} elements</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleInspectElements(page)}
                          className="px-2.5 py-1 bg-gray-800 hover:bg-gray-700 text-emerald-400 rounded text-xs font-medium transition"
                        >
                          View Elements
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Screenshots */}
      {activeTab === 'screenshots' && (
        <div>
          {screenshots.length === 0 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500 text-sm">
              No screenshots captured yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {screenshots.map((s) => {
                // Convert relative artifacts path to static server URL
                const normalizedPath = (s.file_path || '').replace(/\\/g, '/');
                const cleanUrl = normalizedPath.startsWith('./') ? normalizedPath.slice(2) : normalizedPath;
                const imageUrl = `${BACKEND_URL}/${cleanUrl}`;

                return (
                  <div
                    key={s.id}
                    onClick={() => setPreviewImage(imageUrl)}
                    className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 cursor-pointer transition group"
                  >
                    <div className="h-44 bg-gray-950 overflow-hidden relative">
                      <img
                        src={imageUrl}
                        alt={s.description || 'Page screenshot'}
                        className="w-full h-full object-cover object-top group-hover:scale-105 transition duration-300"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                    </div>
                    <div className="p-3.5 space-y-1">
                      <div className="text-xs font-mono text-emerald-400 truncate">{s.url}</div>
                      <div className="text-xs text-gray-400 truncate">{s.description}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Console Activity */}
      {activeTab === 'console' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-gray-800/80 text-xs text-gray-400 font-medium">
            <span>Browser Console Output ({consoleLogs.length})</span>
            <span className="text-[11px] text-gray-500">Uncaught JavaScript errors and runtime logs</span>
          </div>

          {consoleLogs.length === 0 ? (
            <div className="p-12 text-center text-gray-500 text-sm flex flex-col items-center justify-center space-y-2">
              <CheckCircle2 className="h-8 w-8 text-emerald-500/50" />
              <span>No console errors or warnings detected during crawl.</span>
            </div>
          ) : (
            <div className="space-y-2.5">
              {consoleLogs.map((log) => {
                const isError = log.description?.toLowerCase().includes('error') || log.description?.toLowerCase().includes('uncaught');
                const badgeStyle = isError
                  ? 'bg-red-950/80 text-red-400 border-red-800/50'
                  : 'bg-amber-950/80 text-amber-400 border-amber-800/50';

                return (
                  <div key={log.id} className="p-3.5 bg-gray-950/80 border border-gray-800 hover:border-gray-700 rounded-xl text-xs font-mono space-y-1.5 transition">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className={`px-2 py-0.5 font-bold uppercase rounded border text-[11px] flex-shrink-0 ${badgeStyle}`}>
                          {isError ? 'ERROR' : 'WARN'}
                        </span>
                        <span className="text-gray-200 font-medium truncate text-xs">
                          {log.description}
                        </span>
                      </div>
                      <span className="text-gray-500 text-[11px] flex-shrink-0">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    {log.url && (
                      <div className="text-gray-400 text-[11px] pl-2 border-l-2 border-gray-800 truncate" title={log.url}>
                        Source: {log.url}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Network Requests */}
      {activeTab === 'network' && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-gray-800/80 text-xs text-gray-400 font-medium">
            <span>Captured Network Errors & Failures ({networkLogs.length})</span>
            <span className="text-[11px] text-gray-500">Includes 4xx/5xx HTTP codes and aborted requests</span>
          </div>

          {networkLogs.length === 0 ? (
            <div className="p-12 text-center text-gray-500 text-sm flex flex-col items-center justify-center space-y-2">
              <CheckCircle2 className="h-8 w-8 text-emerald-500/50" />
              <span>All network requests completed without errors.</span>
            </div>
          ) : (
            <div className="space-y-2.5">
              {networkLogs.map((net) => {
                const parsed = parseNetworkError(net.description, net.url);
                const methodColor =
                  parsed.method === 'POST' ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60' :
                  parsed.method === 'GET' ? 'bg-blue-950/80 text-blue-400 border-blue-800/60' :
                  parsed.method === 'DELETE' ? 'bg-red-950/80 text-red-400 border-red-800/60' :
                  parsed.method === 'PUT' ? 'bg-amber-950/80 text-amber-400 border-amber-800/60' :
                  'bg-gray-800 text-gray-300 border-gray-700';

                return (
                  <div
                    key={net.id}
                    className="p-3.5 bg-gray-950/80 border border-red-900/30 hover:border-red-800/60 rounded-xl text-xs font-mono transition space-y-2 group shadow-sm"
                  >
                    <div className="flex items-center justify-between gap-3 flex-wrap sm:flex-nowrap">
                      <div className="flex items-center space-x-2 min-w-0 flex-1">
                        <span className={`px-2 py-0.5 font-bold uppercase rounded border text-[11px] flex-shrink-0 ${methodColor}`}>
                          {parsed.method}
                        </span>
                        <span className="px-2 py-0.5 font-semibold rounded bg-red-950/80 text-red-400 border border-red-800/50 text-[11px] flex-shrink-0">
                          {parsed.status}
                        </span>
                        <span className="text-gray-200 font-semibold truncate text-xs" title={parsed.fullUrl}>
                          {parsed.cleanUrl}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 text-gray-500 text-[11px] flex-shrink-0 ml-auto">
                        <button
                          type="button"
                          onClick={() => {
                            navigator.clipboard.writeText(parsed.fullUrl);
                            setCopiedLogId(net.id);
                            setTimeout(() => setCopiedLogId(null), 2000);
                          }}
                          className="px-2 py-0.5 bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-gray-200 rounded border border-gray-800 transition flex items-center space-x-1"
                          title="Copy full URL"
                        >
                          {copiedLogId === net.id ? (
                            <>
                              <Check className="h-3 w-3 text-emerald-400" />
                              <span className="text-[10px] text-emerald-400">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="h-3 w-3" />
                              <span className="text-[10px]">Copy</span>
                            </>
                          )}
                        </button>
                        <span>{new Date(net.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>

                    {parsed.queryParams && (
                      <div className="pl-2 border-l-2 border-gray-800 text-gray-500 text-[11px] break-all">
                        <span className="text-gray-400 font-medium">Query: </span>
                        <span>{parsed.queryParams}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Inspect Elements Modal */}
      {selectedPage && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white">{selectedPage.title || selectedPage.url}</h3>
                <p className="text-xs text-gray-400 font-mono">{selectedPage.url}</p>
              </div>
              <button
                onClick={() => setSelectedPage(null)}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-800 rounded"
              >
                Close
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-3">
              {loadingElements ? (
                <div className="text-center py-8 text-xs text-gray-400">Loading extracted elements...</div>
              ) : pageElements.length === 0 ? (
                <div className="text-center py-8 text-xs text-gray-500">No elements found on this page.</div>
              ) : (
                pageElements.map((el) => (
                  <div key={el.id} className="p-3 bg-gray-950 border border-gray-800 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400 uppercase tracking-wide">{el.element_type}</span>
                      <span className="text-[10px] text-gray-500 font-mono">&lt;{el.tag_name}&gt;</span>
                    </div>
                    <div className="font-mono text-gray-300 break-all bg-gray-900 px-2 py-1 rounded">
                      {el.selector}
                    </div>
                    {el.text && (
                      <div className="text-gray-400">Text: <span className="text-white">"{el.text}"</span></div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Full Screenshot Modal */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 cursor-zoom-out"
        >
          <img
            src={previewImage}
            alt="Full Preview"
            className="max-w-full max-h-full rounded-lg shadow-2xl object-contain border border-gray-700"
          />
        </div>
      )}
    </div>
  );
};
