import React from 'react';
import { Compass, Layers, LayoutDashboard, Terminal, Network, CheckSquare, Activity, Bug as BugIcon, Database } from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, setCurrentTab }) => {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/30">
              <Terminal className="h-6 w-6 text-emerald-400" />
            </div>
            <div>
              <span className="font-bold text-lg text-white tracking-tight">Autonomous QA</span>
            </div>
          </div>


          <div className="flex space-x-1">
            <button
              onClick={() => setCurrentTab('dashboard')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'dashboard'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setCurrentTab('applications')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'applications'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Layers className="h-4 w-4" />
              <span>Applications</span>
            </button>

            <button
              onClick={() => setCurrentTab('exploration')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'exploration'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Compass className="h-4 w-4" />
              <span>Exploration</span>
            </button>

            <button
              onClick={() => setCurrentTab('workflows')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'workflows'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Network className="h-4 w-4" />
              <span>Workflows</span>
            </button>

            <button
              onClick={() => setCurrentTab('test-cases')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'test-cases'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <CheckSquare className="h-4 w-4" />
              <span>Test Cases</span>
            </button>

            <button
              onClick={() => setCurrentTab('executions')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'executions'
                  ? 'bg-gray-800 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Activity className="h-4 w-4" />
              <span>Executions</span>
            </button>

            <button
              onClick={() => setCurrentTab('database')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'database'
                  ? 'bg-gray-800 text-blue-400 border border-blue-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <Database className="h-4 w-4 text-blue-400" />
              <span>Database</span>
            </button>

            <button
              onClick={() => setCurrentTab('bugs')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                currentTab === 'bugs'
                  ? 'bg-gray-800 text-rose-400 border border-rose-500/30'
                  : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
              }`}
            >
              <BugIcon className="h-4 w-4 text-rose-400" />
              <span>Bugs</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

