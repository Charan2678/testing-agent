import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Applications } from './pages/Applications';
import { ApplicationDetails } from './pages/ApplicationDetails';
import { Exploration } from './pages/Exploration';
import { ExplorationResults } from './pages/ExplorationResults';
import { Workflows } from './pages/Workflows';
import { TestCases } from './pages/TestCases';
import { ExecutionsDashboard } from './pages/ExecutionsDashboard';
import { BugsDashboard } from './pages/BugsDashboard';
import { DatabaseQA } from './pages/DatabaseQA';
import { applicationsApi } from './services/api';
import { Application } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [activeAppId, setActiveAppId] = useState<number | undefined>(() => {
    const saved = localStorage.getItem('qa_agent_active_app_id');
    return saved ? Number(saved) : undefined;
  });
  const [contextId, setContextId] = useState<number | undefined>(undefined);
  const [apps, setApps] = useState<Application[]>([]);

  useEffect(() => {
    const loadApps = async () => {
      try {
        const data = await applicationsApi.getAll();
        setApps(data);
        if (data.length > 0) {
          if (!activeAppId || !data.some(a => a.id === activeAppId)) {
            // Prefer an application with data (like App #2) or fallback to first
            const preferred = data.find(a => a.id === 2) || data[0];
            setActiveAppId(preferred.id);
            localStorage.setItem('qa_agent_active_app_id', String(preferred.id));
          }
        }
      } catch (err) {
        console.error('Failed to load apps in App.tsx:', err);
      }
    };
    loadApps();
  }, []);

  const handleSelectApp = (appId: number) => {
    setActiveAppId(appId);
    localStorage.setItem('qa_agent_active_app_id', String(appId));
  };

  const handleNavigate = (tab: string, id?: number) => {
    setCurrentTab(tab);
    if (id !== undefined) {
      setContextId(id);
      if (tab !== 'results') {
        setActiveAppId(id);
        localStorage.setItem('qa_agent_active_app_id', String(id));
      }
    }
    // When clicking navbar (id is undefined), activeAppId remains preserved!
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-black">
      <Navbar currentTab={currentTab} setCurrentTab={(tab) => handleNavigate(tab)} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'dashboard' && <Dashboard onNavigate={handleNavigate} />}
        {currentTab === 'applications' && <Applications onNavigate={handleNavigate} />}
        {currentTab === 'app-details' && (contextId || activeAppId) && (
          <ApplicationDetails appId={(contextId || activeAppId)!} onNavigate={handleNavigate} />
        )}
        {currentTab === 'exploration' && (
          <Exploration initialAppId={contextId || activeAppId} onNavigate={handleNavigate} />
        )}
        {currentTab === 'results' && contextId && (
          <ExplorationResults runId={contextId} onNavigate={handleNavigate} />
        )}
        {currentTab === 'workflows' && (
          <Workflows
            initialAppId={activeAppId}
            onSelectApp={handleSelectApp}
            onNavigate={handleNavigate}
          />
        )}
        {currentTab === 'test-cases' && (
          <TestCases
            initialAppId={activeAppId}
            onSelectApp={handleSelectApp}
            onNavigate={handleNavigate}
          />
        )}
        {currentTab === 'executions' && (
          <ExecutionsDashboard
            initialAppId={activeAppId}
            onSelectApp={handleSelectApp}
            onNavigate={handleNavigate}
          />
        )}
        {currentTab === 'database' && (
          <DatabaseQA
            initialAppId={activeAppId}
            onSelectApp={handleSelectApp}
            onNavigate={handleNavigate}
          />
        )}
        {currentTab === 'bugs' && (
          <BugsDashboard
            initialAppId={activeAppId}
            onSelectApp={handleSelectApp}
            onNavigate={handleNavigate}
          />
        )}
      </main>

      <footer className="border-t border-gray-800/80 py-6 text-center text-xs text-gray-500">
        Autonomous AI Testing & QA Agent • Database QA & Data Integrity Engine • Zero Mock Data
      </footer>
    </div>
  );
};

export default App;
