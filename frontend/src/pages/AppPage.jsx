import React, { useState } from 'react';
import NavBar from '../components/layout/NavBar';
import Sidebar from '../components/layout/Sidebar';
import RightPanel from '../components/layout/RightPanel';
import QueryInput from '../components/research/QueryInput';
import AgentPipeline from '../components/research/AgentPipeline';
import ResultsPanel from '../components/research/ResultsPanel';
import EmptyState from '../components/shared/EmptyState';
import { useQuery } from '../hooks/useQuery';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';

export default function AppPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const { result, loading, agentStatus, error, submitQuery, submitPDF } = useQuery();

  const handleSelectHistory = (query) => {
    submitQuery(query);
  };

  return (
    <div className="h-screen bg-parchment flex flex-col overflow-hidden">
      <NavBar />

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(v => !v)}
          onSelectQuery={handleSelectHistory}
          activeQuery={result?.query}
        />

        {/* Center workspace */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Sidebar toggle */}
          <div className="h-10 border-b border-stone bg-white flex items-center px-3">
            <button
              onClick={() => setSidebarCollapsed(v => !v)}
              className="btn-ghost p-1.5"
              title={sidebarCollapsed ? 'Show history' : 'Hide history'}
            >
              {sidebarCollapsed
                ? <PanelLeftOpen size={15} className="text-mist" />
                : <PanelLeftClose size={15} className="text-mist" />
              }
            </button>
          </div>

          {/* Scrollable content area */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-6 py-6">

              {/* Query input always at top */}
              <QueryInput
                onSubmit={submitQuery}
                onPDF={submitPDF}
                loading={loading}
              />

              {/* Agent pipeline visualiser — shown while loading */}
              {loading && (
                <div className="mt-6">
                  <AgentPipeline currentStage={agentStatus} />
                </div>
              )}

              {/* Error */}
              {error && !loading && (
                <div className="mt-6 p-4 rounded-card border border-danger-light bg-danger-light">
                  <p className="text-sm text-danger">{error}</p>
                </div>
              )}

              {/* Results */}
              {result && !loading && (
                <div className="mt-6">
                  <ResultsPanel
                    result={result}
                    onOpenIntelligence={() => setRightPanelOpen(true)}
                  />
                </div>
              )}

              {/* Empty state */}
              {!result && !loading && !error && (
                <div className="mt-12">
                  <EmptyState onSampleQuery={submitQuery} />
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Right intelligence panel */}
        {rightPanelOpen && (
          <RightPanel result={result} onClose={() => setRightPanelOpen(false)} />
        )}
      </div>
    </div>
  );
}