import React from 'react';
import {
  LayoutDashboard,
  Ticket as TicketIcon,
  Users,
  Compass,
  Clock,
  AlertTriangle,
  FlaskConical,
  Settings,
  ShieldCheck,
  Radio
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  openTicketsCount: number;
  anomaliesCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  openTicketsCount,
  anomaliesCount,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Operations Dashboard', icon: LayoutDashboard },
    { id: 'simulator', label: 'Omnichannel Tester (Email/Chat/Call)', icon: Radio, badgeColor: 'bg-emerald-600', badge: 1 },
    { id: 'tickets', label: 'Ticket Workspace', icon: TicketIcon, badge: openTicketsCount },
    { id: 'agents', label: 'Agent Capacity Roster', icon: Users },
    { id: 'routing', label: 'Routing Decision Explorer', icon: Compass },
    { id: 'sla', label: 'SLA Monitoring', icon: Clock },
    { id: 'anomalies', label: 'Anomaly Center', icon: AlertTriangle, badge: anomaliesCount, badgeColor: 'bg-red-500' },
    { id: 'evaluation', label: 'Evaluation Lab', icon: FlaskConical },
    { id: 'config', label: 'System Configuration', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800 select-none">
      <div className="p-5 border-b border-slate-800 flex items-center space-x-3">
        <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div>
          <h1 className="font-bold text-white text-sm tracking-wide">OMNICORE ROUTER</h1>
          <p className="text-xs text-slate-400">Enterprise SLA Platform</p>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'hover:bg-slate-800/80 hover:text-white'
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full text-white ${
                    item.badgeColor || (isActive ? 'bg-blue-700' : 'bg-slate-700')
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400">
        <div className="flex items-center justify-between mb-1">
          <span>Routing Engine</span>
          <span className="text-emerald-400 font-mono font-medium">v1.0 ACTIVE</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Seed Reproducibility</span>
          <span className="font-mono text-slate-300">20261022</span>
        </div>
      </div>
    </aside>
  );
};
