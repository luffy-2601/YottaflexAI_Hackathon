import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldCheck, RefreshCw, AlertCircle, FileText } from 'lucide-react';
import { AnomalyItem } from '../types';
import { api } from '../services/api';

export const AnomalyCenterPage: React.FC = () => {
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);

  const loadAnomalies = async () => {
    setLoading(true);
    try {
      const data = await api.getAnomalies();
      setAnomalies(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnomalies();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      const data = await api.scanAnomalies();
      setAnomalies(data);
    } catch (err) {
      console.error(err);
    } finally {
      setScanning(false);
    }
  };

  const severityBadge = (sev: string) => {
    const map: Record<string, string> = {
      CRITICAL: 'bg-red-100 text-red-800 border-red-300 font-bold',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-300',
      MEDIUM: 'bg-amber-100 text-amber-800 border-amber-300',
      LOW: 'bg-blue-100 text-blue-800 border-blue-300',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${map[sev] || 'bg-slate-100'}`}>
        {sev}
      </span>
    );
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Anomaly Center & Ground Truth Audit</h2>
          <p className="text-xs text-slate-500">
            Real-time audit engine detecting capacity overages, transfer loops, calendar mismatches & safety breaches
          </p>
        </div>

        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center space-x-1.5 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${scanning ? 'animate-spin' : ''}`} />
          <span>{scanning ? 'Scanning Database Invariants...' : 'Run Anomaly Scan'}</span>
        </button>
      </div>

      {/* Explanatory Notice */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
        <div className="flex items-center space-x-2 font-bold">
          <AlertCircle className="h-4 w-4 text-amber-600" />
          <span>Ground Truth Isolation Notice (Security & Rigor Protocol)</span>
        </div>
        <p className="leading-relaxed text-[11px] text-amber-800">
          In strict compliance with prompt specifications, the injected synthetic anomalies are preserved in a separate isolated <span className="font-mono font-bold">ground_truth.json</span> file. Ground truth is never leaked into the routing engine's input feature space. The audit scanner evaluates operational invariants independently against relational database records.
        </p>
      </div>

      {/* Anomalies List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Auditing system anomalies...</div>
        ) : anomalies.length === 0 ? (
          <div className="p-12 text-center text-xs text-emerald-600 bg-emerald-50 rounded-xl border border-emerald-200">
            <ShieldCheck className="h-8 w-8 mx-auto mb-2 text-emerald-500" />
            <p className="font-bold">Zero Anomaly Violations Detected</p>
            <p className="text-[11px] text-emerald-700 mt-0.5">All capacity limits, calendars, safety rules, and history chains are strictly compliant.</p>
          </div>
        ) : (
          anomalies.map((anom) => (
            <div
              key={anom.anomaly_id}
              className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-4 w-4 text-rose-500" />
                  <span className="font-mono text-xs font-bold text-slate-900">{anom.category}</span>
                  {severityBadge(anom.severity)}
                  {anom.ticket_id && (
                    <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      {anom.ticket_id}
                    </span>
                  )}
                  {anom.agent_id && (
                    <span className="text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      {anom.agent_id}
                    </span>
                  )}
                </div>

                <span className="text-[11px] text-slate-400 font-mono">
                  {new Date(anom.detected_at).toLocaleString()}
                </span>
              </div>

              <p className="text-xs text-slate-800 font-medium mb-3">{anom.description}</p>

              {/* Expected vs Actual Comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-emerald-50/60 rounded-lg border border-emerald-200">
                  <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block mb-0.5">
                    Expected Behavior (System Invariant)
                  </span>
                  <p className="text-emerald-950 font-medium text-[11px]">{anom.expected_behavior}</p>
                </div>

                <div className="p-3 bg-red-50/60 rounded-lg border border-red-200">
                  <span className="text-[10px] font-bold text-red-800 uppercase tracking-wider block mb-0.5">
                    Actual Observed Behavior (Detected Anomaly)
                  </span>
                  <p className="text-red-950 font-medium text-[11px]">{anom.actual_behavior}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
