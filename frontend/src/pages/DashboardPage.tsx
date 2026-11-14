import React from 'react';
import {
  Ticket, CheckCircle2, Clock, AlertTriangle, Users,
  ShieldAlert, ThumbsUp, TrendingUp, Layers
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { OperationsOverview } from '../types';

interface DashboardProps {
  data: OperationsOverview | null;
  loading: boolean;
}

const PRIORITY_COLORS: Record<string, string> = {
  P1: '#ef4444',
  P2: '#f97316',
  P3: '#3b82f6',
  P4: '#10b981',
};

const CHANNEL_COLORS: Record<string, string> = {
  email: '#6366f1',
  chat: '#06b6d4',
  phone: '#8b5cf6',
};

export const DashboardPage: React.FC<DashboardProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
        <span>Calculating operations metrics from live persistence store...</span>
      </div>
    );
  }

  const kpis = [
    { label: 'Total Tickets', val: data.total_tickets.toLocaleString(), icon: Ticket, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Open Workload', val: data.open_tickets.toLocaleString(), icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Resolved Tickets', val: data.resolved_tickets.toLocaleString(), icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'SLA Compliance', val: `${data.sla_compliance_pct}%`, icon: TrendingUp, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'SLA Breaches', val: data.sla_breaches_count, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Avg First Response', val: `${data.avg_first_response_minutes}m`, icon: Clock, color: 'text-cyan-600', bg: 'bg-cyan-50' },
    { label: 'Avg Resolution Time', val: `${data.avg_resolution_minutes}m`, icon: Layers, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Active Agents', val: `${data.active_agents} (${data.overall_utilization_pct}% Utl)`, icon: Users, color: 'text-teal-600', bg: 'bg-teal-50' },
    { label: 'Critical P1s', val: data.critical_incidents, icon: ShieldAlert, color: 'text-rose-600', bg: 'bg-rose-50' },
    { label: 'Customer CSAT', val: `${data.avg_csat} / 5.0`, icon: ThumbsUp, color: 'text-emerald-600', bg: 'bg-emerald-50' },
  ];

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex items-center space-x-3">
              <div className={`p-2.5 rounded-lg ${kpi.bg} ${kpi.color}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">{kpi.label}</p>
                <p className="text-xl font-bold text-slate-900 mt-0.5">{kpi.val}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Channel Volume Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-800">Tickets by Ingestion Channel</h3>
            <span className="text-xs text-slate-400">Omnichannel Spread</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.distributions.channel}>
                <XAxis dataKey="channel" tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
                <Tooltip />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {data.distributions.channel.map((entry) => (
                    <Cell key={entry.channel} fill={CHANNEL_COLORS[entry.channel] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Priority Breakdown Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-800">Priority Severity Breakdown</h3>
            <span className="text-xs text-slate-400">P1 Critical to P4 Low</span>
          </div>
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.distributions.priority}
                  dataKey="count"
                  nameKey="priority"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={45}
                  paddingAngle={4}
                  label={(entry: any) => `${entry.priority}: ${entry.count}`}
                >
                  {data.distributions.priority.map((entry) => (
                    <Cell key={entry.priority} fill={PRIORITY_COLORS[entry.priority] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top Intents & Lifecycle Funnel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">Top Incoming Customer Intents</h3>
          <div className="space-y-3">
            {data.distributions.intent.map((item) => {
              const maxCount = Math.max(...data.distributions.intent.map((x) => x.count), 1);
              const pct = Math.round((item.count / maxCount) * 100);
              return (
                <div key={item.intent} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-700 font-mono">{item.intent}</span>
                    <span className="text-slate-500">{item.count} tickets</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">Operational Status Funnel</h3>
          <div className="space-y-2.5">
            {data.distributions.status.map((item) => (
              <div key={item.status} className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg text-xs">
                <span className="font-semibold text-slate-700">{item.status}</span>
                <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-800 font-bold">
                  {item.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
