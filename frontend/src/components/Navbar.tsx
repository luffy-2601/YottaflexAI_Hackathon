import React from 'react';
import { Activity, RefreshCw, ShieldCheck, LogIn, LogOut, User as UserIcon } from 'lucide-react';

interface NavbarProps {
  title: string;
  onRefresh: () => void;
  isRefreshing: boolean;
  currentUser: { email: string; role: string; tenant_id: string } | null;
  onOpenLogin: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  title,
  onRefresh,
  isRefreshing,
  currentUser,
  onOpenLogin,
  onLogout
}) => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 shadow-xs">
      <div className="flex items-center space-x-3">
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 mr-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
          Live Ingestion
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {currentUser ? (
          <div className="flex items-center space-x-2 bg-slate-100 py-1 px-3 rounded-lg border border-slate-200 text-xs">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span className="font-semibold text-slate-700">{currentUser.email}</span>
            <span className="bg-blue-600 text-white font-bold px-1.5 py-0.5 rounded text-[10px] uppercase">
              {currentUser.role}
            </span>
            <button
              onClick={onLogout}
              title="Sign Out"
              className="text-slate-400 hover:text-rose-600 ml-1 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors shadow-xs"
          >
            <LogIn className="h-3.5 w-3.5" />
            <span>Sign In (JWT)</span>
          </button>
        )}

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Sync Data</span>
        </button>

        <div className="flex items-center space-x-2 pl-3 border-l border-slate-200 text-xs text-slate-500">
          <Activity className="h-4 w-4 text-blue-500" />
          <span>Tier 3 Relational DB (WAL)</span>
        </div>
      </div>
    </header>
  );
};
