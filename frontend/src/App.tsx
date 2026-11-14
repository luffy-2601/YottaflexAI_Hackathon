import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { TicketsPage } from './pages/TicketsPage';
import { AgentsPage } from './pages/AgentsPage';
import { RoutingExplorerPage } from './pages/RoutingExplorerPage';
import { SLAMonitorPage } from './pages/SLAMonitorPage';
import { AnomalyCenterPage } from './pages/AnomalyCenterPage';
import { EvaluationLabPage } from './pages/EvaluationLabPage';
import { ConfigPage } from './pages/ConfigPage';
import { OperationsOverview, AnomalyItem } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [overview, setOverview] = useState<OperationsOverview | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Authentication State
  const [currentUser, setCurrentUser] = useState<{ email: string; role: string; tenant_id: string } | null>(() => {
    const saved = localStorage.getItem('omniroute_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loginModalOpen, setLoginModalOpen] = useState<boolean>(false);
  const [loginEmail, setLoginEmail] = useState<string>('admin.evaluator@hackathon.org');
  const [loginPassword, setLoginPassword] = useState<string>('SecureEnterprisePassword2026!');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await api.login({ email: loginEmail, password: loginPassword });
      localStorage.setItem('omniroute_token', res.access_token);
      const userObj = { email: res.email, role: res.role, tenant_id: res.tenant_id };
      localStorage.setItem('omniroute_user', JSON.stringify(userObj));
      setCurrentUser(userObj);
      setLoginModalOpen(false);
      loadGlobalData();
    } catch (err: any) {
      setAuthError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
  };

  useEffect(() => {
    const handleAuthExpired = () => setCurrentUser(null);
    window.addEventListener('omniroute_auth_expired', handleAuthExpired);
    return () => window.removeEventListener('omniroute_auth_expired', handleAuthExpired);
  }, []);

  const loadGlobalData = async () => {
    setRefreshing(true);
    try {
      const [ovRes, anomRes] = await Promise.all([
        api.getOverview(),
        api.getAnomalies(),
      ]);
      setOverview(ovRes);
      setAnomalies(anomRes);
    } catch (err) {
      console.error('Failed to load global operations data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadGlobalData();
    const interval = setInterval(loadGlobalData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    switch (currentTab) {
      case 'dashboard': return 'Live Operations Dashboard';
      case 'simulator': return 'Omnichannel Ingestion Tester (Email, Chatbot & Voice Calls)';
      case 'tickets': return 'Omnichannel Ticket Workspace';
      case 'agents': return 'Agent Capacity & Competency Roster';
      case 'routing': return 'Intelligent Routing Decision Inspector';
      case 'sla': return 'SLA Monitoring & Deadline Urgency';
      case 'anomalies': return 'System Invariant & Anomaly Center';
      case 'evaluation': return 'Routing Strategy Benchmark Lab';
      case 'config': return 'System Policies & Dynamic Weights';
      default: return 'Omnichannel Management Platform';
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans antialiased text-slate-900 overflow-hidden">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        openTicketsCount={overview?.open_tickets || 0}
        anomaliesCount={anomalies.length}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          title={getPageTitle()}
          onRefresh={loadGlobalData}
          isRefreshing={refreshing}
          currentUser={currentUser}
          onOpenLogin={() => setLoginModalOpen(true)}
          onLogout={handleLogout}
        />

        <main className={`flex-1 relative ${currentTab === 'tickets' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
          {currentTab === 'dashboard' && <DashboardPage data={overview} loading={loading} />}
          {currentTab === 'simulator' && <SimulatorPage />}
          {currentTab === 'tickets' && <TicketsPage onTicketUpdated={loadGlobalData} />}
          {currentTab === 'agents' && <AgentsPage />}
          {currentTab === 'routing' && <RoutingExplorerPage />}
          {currentTab === 'sla' && <SLAMonitorPage />}
          {currentTab === 'anomalies' && <AnomalyCenterPage />}
          {currentTab === 'evaluation' && <EvaluationLabPage />}
          {currentTab === 'config' && <ConfigPage />}
        </main>
      </div>

      {/* JWT Login Modal */}
      {loginModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 border border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800">OmniRoute Enterprise Sign-In</h3>
              <button
                onClick={() => setLoginModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogin} className="mt-4 space-y-4">
              {authError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                  {authError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Corporate Email</label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-hidden"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-hidden"
                  required
                />
              </div>

              {/* 1-Click Preset Buttons for Hackathon Judges */}
              <div className="pt-2">
                <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">1-Click Fast Presets:</span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setLoginEmail('admin.evaluator@hackathon.org');
                      setLoginPassword('SecureEnterprisePassword2026!');
                    }}
                    className="px-2.5 py-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 text-[11px] rounded-md font-medium text-left"
                  >
                    🔑 Admin Evaluator
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setLoginEmail('agent.smith@matrix.com');
                      setLoginPassword('CorrectHorseBatteryStaple123');
                    }}
                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-[11px] rounded-md font-medium text-left"
                  >
                    👤 Support Agent
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setLoginModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={authLoading}
                  className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {authLoading ? 'Verifying...' : 'Sign In with JWT'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
