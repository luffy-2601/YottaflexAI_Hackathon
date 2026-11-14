import React, { useState, useEffect } from 'react';
import { Users, Award, Globe, Clock, CheckCircle2, PauseCircle, XCircle } from 'lucide-react';
import { Agent } from '../types';
import { api } from '../services/api';

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('');

  const loadAgents = async () => {
    setLoading(true);
    try {
      const data = await api.getAgents(filterStatus || undefined);
      setAgents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, [filterStatus]);

  const handleStatusChange = async (agentId: string, newStatus: string) => {
    try {
      await api.updateAgentStatus(agentId, newStatus);
      loadAgents();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Control Bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900">Support Agent Capacity & Roster</h2>
          <p className="text-xs text-slate-500">Live agent shifts, skill competencies, and real-time concurrency load</p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs bg-white border border-slate-200 rounded-lg px-3 py-1.5 font-medium text-slate-700 shadow-2xs"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="ON_BREAK">ON_BREAK</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>
        </div>
      </div>

      {/* Agents Grid */}
      {loading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading agent roster...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => {
            const availSlots = agent.max_concurrency - agent.current_active_tickets;
            const isFull = availSlots <= 0;
            return (
              <div
                key={agent.agent_id}
                className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 flex flex-col justify-between hover:shadow-xs transition-shadow"
              >
                <div>
                  {/* Top Bar */}
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-sm text-slate-800">{agent.name}</span>
                        <span className="font-mono text-[10px] text-slate-400">({agent.agent_id})</span>
                      </div>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">{agent.email}</p>
                    </div>

                    <select
                      value={agent.status}
                      onChange={(e) => handleStatusChange(agent.agent_id, e.target.value)}
                      className={`text-[11px] font-semibold rounded-full px-2 py-0.5 border cursor-pointer ${
                        agent.status === 'ACTIVE'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : agent.status === 'ON_BREAK'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="ON_BREAK">ON_BREAK</option>
                      <option value="INACTIVE">INACTIVE</option>
                    </select>
                  </div>

                  {/* Capacity Bar */}
                  <div className="mb-4 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <div className="flex justify-between text-xs mb-1 font-medium">
                      <span className="text-slate-600">Active Load: {agent.current_active_tickets} / {agent.max_concurrency}</span>
                      <span className={`font-semibold ${isFull ? 'text-red-600' : 'text-blue-600'}`}>
                        {agent.utilization_rate}% Utl ({availSlots} slot{availSlots === 1 ? '' : 's'} free)
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          isFull ? 'bg-red-500' : agent.utilization_rate > 50 ? 'bg-amber-500' : 'bg-blue-600'
                        }`}
                        style={{ width: `${Math.min(100, agent.utilization_rate)}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Skills Section */}
                  <div className="space-y-2 mb-3">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Skills</span>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.skills.map((s) => (
                        <span
                          key={s.skill_id}
                          className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-mono border border-blue-200"
                        >
                          {s.skill_id} ({Math.round(s.proficiency_level * 100)}%)
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Languages Section */}
                  <div className="space-y-1 mb-3">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Languages</span>
                    <div className="flex flex-wrap gap-1.5">
                      {agent.languages.map((l) => (
                        <span
                          key={l.language_code}
                          className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-mono uppercase font-bold"
                        >
                          {l.language_code}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Footer Experience Score */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <span>Exp Score: {agent.experience_score}</span>
                  <span className="text-[11px] text-slate-400">Shift: Mon-Fri 09-18 IST</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
