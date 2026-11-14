import React, { useState, useEffect } from 'react';
import { Compass, CheckCircle2, XCircle, Award, Scale, HelpCircle } from 'lucide-react';
import { Ticket, RoutingDecisionEvaluation } from '../types';
import { api } from '../services/api';

export const RoutingExplorerPage: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string>('');
  const [evaluation, setEvaluation] = useState<RoutingDecisionEvaluation | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    api.getTickets().then((data) => {
      setTickets(data);
      if (data.length > 0) {
        setSelectedTicketId(data[0].ticket_id);
      }
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedTicketId) return;
    setLoading(true);
    api.evaluateRouting(selectedTicketId)
      .then(setEvaluation)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedTicketId]);

  const selectedTicket = tickets.find((t) => t.ticket_id === selectedTicketId);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Intelligent Routing Decision Inspector</h2>
          <p className="text-xs text-slate-500">
            Audit candidate scoring, hard constraint rejections, and explainable AI routing logic
          </p>
        </div>

        {/* Ticket Selector */}
        <div className="flex items-center space-x-2">
          <label className="text-xs font-semibold text-slate-600">Inspect Ticket:</label>
          <select
            value={selectedTicketId}
            onChange={(e) => setSelectedTicketId(e.target.value)}
            className="text-xs bg-white border border-slate-200 rounded-lg px-3 py-1.5 font-mono font-medium text-slate-800 shadow-2xs"
          >
            {tickets.map((t) => (
              <option key={t.ticket_id} value={t.ticket_id}>
                {t.ticket_id} - [{t.priority}] {t.subject.slice(0, 45)}...
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="p-16 text-center text-xs text-slate-400">
          Evaluating two-stage multi-factor routing pipeline...
        </div>
      ) : evaluation && selectedTicket ? (
        <div className="space-y-6">
          {/* Explanation Banner */}
          <div className="p-5 bg-blue-50/80 border border-blue-200 rounded-xl flex items-start space-x-3.5 shadow-2xs">
            <div className="p-2 bg-blue-600 text-white rounded-lg shrink-0 mt-0.5">
              <Compass className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <h4 className="text-xs font-bold text-blue-900 uppercase tracking-wider mb-1">
                Deterministic Assignment Explanation
              </h4>
              <p className="text-sm text-blue-950 font-medium leading-relaxed">
                {evaluation.explanation}
              </p>
              <div className="mt-2 flex items-center space-x-4 text-[11px] text-blue-700 font-mono">
                <span>Selected: <strong>{evaluation.selected_agent_id || 'NONE'}</strong></span>
                <span>•</span>
                <span>Final Score: <strong>{evaluation.final_score ?? 'N/A'}</strong></span>
                <span>•</span>
                <span>Eligible Candidates: <strong>{evaluation.eligible_count}</strong></span>
              </div>
            </div>
          </div>

          {/* Ticket Hard Requirements */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Stage 1: Hard Eligibility Filters Required
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[11px]">Classified Intent</span>
                <span className="font-mono font-bold text-slate-800">{selectedTicket.intent_id}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[11px]">Required Language</span>
                <span className="font-mono font-bold text-slate-800 uppercase">
                  {selectedTicket.language_code} (or English fallback)
                </span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[11px]">Operational Priority</span>
                <span className="font-mono font-bold text-slate-800">{selectedTicket.priority}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block text-[11px]">Required Presence</span>
                <span className="font-bold text-emerald-700">ACTIVE & On-Shift Schedule</span>
              </div>
            </div>
          </div>

          {/* Stage 2: Weighted Candidate Matrix */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                  Stage 2: Multi-Factor Weighted Scoring Matrix
                </h3>
                <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                  Formula: Score = 0.35 * Skill + 0.25 * Lang + 0.25 * Capacity + 0.15 * Experience
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 bg-blue-100 text-blue-800 rounded font-semibold">
                {evaluation.candidate_scores.length} Eligible
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100/70 text-slate-600 font-bold uppercase text-[10px] tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="p-3">Rank / Agent</th>
                    <th className="p-3">Skill Score (35%)</th>
                    <th className="p-3">Lang Score (25%)</th>
                    <th className="p-3">Capacity Score (25%)</th>
                    <th className="p-3">Experience (15%)</th>
                    <th className="p-3 text-right">Total Score (0-100)</th>
                    <th className="p-3 text-center">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium">
                  {evaluation.candidate_scores.map((cand, idx) => {
                    const isSelected = cand.agent_id === evaluation.selected_agent_id;
                    return (
                      <tr key={cand.agent_id} className={isSelected ? 'bg-emerald-50/60 font-semibold' : 'hover:bg-slate-50'}>
                        <td className="p-3">
                          <div className="flex items-center space-x-2">
                            <span className="text-slate-400 font-mono">#{idx + 1}</span>
                            <span className="text-slate-900 font-bold">{cand.agent_name}</span>
                            <span className="font-mono text-slate-400 text-[10px]">({cand.agent_id})</span>
                          </div>
                        </td>
                        <td className="p-3 font-mono">{cand.skill_score.toFixed(1)}</td>
                        <td className="p-3 font-mono">{cand.language_score.toFixed(1)}</td>
                        <td className="p-3 font-mono">{cand.capacity_score.toFixed(1)}</td>
                        <td className="p-3 font-mono">{cand.experience_score.toFixed(1)}</td>
                        <td className="p-3 text-right font-mono font-bold text-blue-600 text-sm">
                          {cand.total_score.toFixed(2)}
                        </td>
                        <td className="p-3 text-center">
                          {isSelected ? (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                              <CheckCircle2 className="h-3 w-3" />
                              <span>SELECTED</span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400">Available</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Rejected Candidates Matrix */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                Stage 1 Filter Audit: Rejected Candidates & Rejection Reasons
              </h3>
              <span className="text-xs px-2.5 py-1 bg-red-100 text-red-800 rounded font-semibold">
                {evaluation.rejected_candidates.length} Ineligible
              </span>
            </div>

            <div className="divide-y divide-slate-100 text-xs">
              {evaluation.rejected_candidates.map((rej) => (
                <div key={rej.agent_id} className="p-3 flex items-start justify-between space-x-4 hover:bg-slate-50">
                  <div className="flex items-center space-x-2">
                    <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                    <div>
                      <span className="font-bold text-slate-800">{rej.agent_name}</span>
                      <span className="text-slate-400 font-mono text-[11px] ml-1.5">({rej.agent_id})</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5 justify-end">
                    {rej.reasons.map((r, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-red-50 text-red-700 text-[11px] font-medium border border-red-200">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
