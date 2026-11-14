import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle, CheckCircle2, ShieldAlert, Calendar } from 'lucide-react';
import { api } from '../services/api';

export const SLAMonitorPage: React.FC = () => {
  const [summary, setSummary] = useState<{ total_monitored: number; breached_count: number; compliance_pct: number; approaching_breach_count: number } | null>(null);
  const [activeSlas, setActiveSlas] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sumRes, actRes] = await Promise.all([
        api.getSLASummary(),
        api.getActiveSLAs(),
      ]);
      setSummary(sumRes);
      setActiveSlas(actRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div>
        <h2 className="text-base font-bold text-slate-900">SLA Engine & Breach Countdown Monitor</h2>
        <p className="text-xs text-slate-500">
          Tracking resolution & response deadlines across business calendars and channel multipliers
        </p>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Monitored Records</p>
              <p className="text-xl font-bold text-slate-900">{summary.total_monitored.toLocaleString()}</p>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Compliance Rate</p>
              <p className="text-xl font-bold text-emerald-600">{summary.compliance_pct}%</p>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-amber-50 text-amber-600">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Approaching (&lt;2h)</p>
              <p className="text-xl font-bold text-amber-600">{summary.approaching_breach_count}</p>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-red-50 text-red-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">SLA Breaches</p>
              <p className="text-xl font-bold text-red-600">{summary.breached_count}</p>
            </div>
          </div>
        </div>
      )}

      {/* Real-time ML Prediction & Queue Dispatcher Panel */}
      <div className="bg-gradient-to-r from-indigo-900 to-slate-900 text-white rounded-xl p-5 shadow-lg border border-indigo-700/50">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-indigo-800">
          <div>
            <div className="flex items-center space-x-2">
              <span className="bg-indigo-500/30 text-indigo-200 text-[10px] font-bold px-2 py-0.5 rounded border border-indigo-400/40 uppercase tracking-wider">
                Production ML Model: v1.0 Calibrated Logistic Regression
              </span>
              <span className="text-xs text-emerald-400 font-semibold flex items-center">
                ● Model Active (800 Trained, Zero Target Leakage)
              </span>
            </div>
            <h3 className="text-sm font-bold mt-1 text-white">Probabilistic SLA Breach Risk Forecaster & Autonomous Dispatcher</h3>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={async () => {
                try {
                  const res = await api.dispatchQueue('default_tenant');
                  alert(`Autonomous Dispatch Complete! Serviced ${res.agents_serviced} agents, dispatched ${res.total_dispatched} queued tickets.`);
                  loadData();
                } catch (e: any) {
                  alert(`Queue dispatch error: ${e.message}`);
                }
              }}
              className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-all shadow-md flex items-center space-x-1.5"
            >
              <span>⚡ Run In-Queue Dispatcher</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-xs">
          <div className="bg-indigo-950/60 p-3 rounded-lg border border-indigo-800/60">
            <span className="text-indigo-300 font-semibold block text-[11px]">Dynamic Training Ground Truth</span>
            <p className="text-slate-200 mt-1">1,000 Historical Tickets • 175 Ground Truth Breaches • Stratified 80/20 Test Split</p>
          </div>
          <div className="bg-indigo-950/60 p-3 rounded-lg border border-indigo-800/60">
            <span className="text-indigo-300 font-semibold block text-[11px]">Independent Scheduler Watchdog</span>
            <p className="text-slate-200 mt-1">Background APScheduler running every 60s for automatic L1/L2/L3 escalations.</p>
          </div>
          <div className="bg-indigo-950/60 p-3 rounded-lg border border-indigo-800/60">
            <span className="text-indigo-300 font-semibold block text-[11px]">Security & Rate Limiting</span>
            <p className="text-slate-200 mt-1">NIST PBKDF2 Password Hashing • HS256 JWT RBAC • 300 req/min Token Bucket Guard</p>
          </div>
        </div>
      </div>

      {/* SLA Policy Reference Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 text-xs space-y-2">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold">
            <Calendar className="h-4 w-4" />
            <span>Business Hours Calendar</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            P2, P3, and P4 deadlines calculate exclusively within Monday–Friday 09:00 to 18:00 IST. Weekends and holidays pause the resolution timer.
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-xs space-y-2">
          <div className="flex items-center space-x-2 text-rose-700 font-bold">
            <ShieldAlert className="h-4 w-4" />
            <span>P1 Critical Invariant</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            P1 Critical tickets run on 24x7x365 continuous wall-clock time (First Response: 5 mins, Resolution: 60 mins). Never paused for off-hours.
          </p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-xs space-y-2">
          <div className="flex items-center space-x-2 text-cyan-700 font-bold">
            <Clock className="h-4 w-4" />
            <span>Channel Multipliers</span>
          </div>
          <p className="text-slate-600 leading-relaxed">
            Phone / Voice has a 0.2x synchronous multiplier (<span className="font-bold">1 min response</span>), Chat has 0.5x, and Email uses standard 1.0x factor.
          </p>
        </div>
      </div>

      {/* Active Countdowns Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
            Urgent SLA Countdowns (Sorted by Resolution Urgency)
          </h3>
          <span className="text-xs text-slate-400">Live Auto-Refresh 30s</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100/70 text-slate-600 font-bold uppercase text-[10px] tracking-wider border-b border-slate-200">
              <tr>
                <th className="p-3">Ticket ID</th>
                <th className="p-3">Priority</th>
                <th className="p-3">Channel</th>
                <th className="p-3">Assigned Agent</th>
                <th className="p-3">Resolution Target</th>
                <th className="p-3 text-right">Time Remaining</th>
                <th className="p-3 text-center">SLA Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400">Loading active countdowns...</td>
                </tr>
              ) : activeSlas.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400">No active running SLAs.</td>
                </tr>
              ) : (
                activeSlas.map((item) => {
                  const isBreached = item.is_breached;
                  const isUrgent = item.minutes_remaining < 60 && !isBreached;
                  return (
                    <tr key={item.ticket_id} className="hover:bg-slate-50">
                      <td className="p-3">
                        <span className="font-mono font-bold text-slate-900">{item.ticket_id}</span>
                        <p className="text-[11px] text-slate-500 line-clamp-1">{item.subject}</p>
                      </td>
                      <td className="p-3 font-mono font-bold">{item.priority}</td>
                      <td className="p-3 font-semibold text-slate-600 uppercase text-[11px]">{item.channel_id}</td>
                      <td className="p-3 font-mono text-slate-700">{item.assigned_agent_id || 'QUEUED'}</td>
                      <td className="p-3 text-slate-600">
                        {new Date(item.resolution_due_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' })}
                      </td>
                      <td className={`p-3 text-right font-mono font-bold ${
                        isBreached ? 'text-red-600' : isUrgent ? 'text-amber-600' : 'text-slate-800'
                      }`}>
                        {item.minutes_remaining > 0 ? `${item.minutes_remaining} mins` : `${Math.abs(item.minutes_remaining)}m OVERDUE`}
                      </td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isBreached
                            ? 'bg-red-100 text-red-800 border border-red-300'
                            : isUrgent
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        }`}>
                          {isBreached ? 'BREACHED' : isUrgent ? 'WARNING' : 'HEALTHY'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
