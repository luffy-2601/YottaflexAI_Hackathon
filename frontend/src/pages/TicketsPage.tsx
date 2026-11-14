import React, { useState, useEffect } from 'react';
import {
  Search, Plus, Filter, MessageSquare, ArrowRightLeft,
  AlertCircle, CheckCircle, RotateCcw, Send, Star, User, Clock
} from 'lucide-react';
import { Ticket, Agent } from '../types';
import { api } from '../services/api';

interface TicketsPageProps {
  onTicketUpdated: () => void;
}

export const TicketsPage: React.FC<TicketsPageProps> = ({ onTicketUpdated }) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  // Modals & Action States
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showTransferModal, setShowTransferModal] = useState<boolean>(false);
  const [showResolveModal, setShowResolveModal] = useState<boolean>(false);

  // Form states
  const [newSubject, setNewSubject] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newChannel, setNewChannel] = useState('email');
  const [newCustomerId, setNewCustomerId] = useState('CUS-000001');
  const [replyBody, setReplyBody] = useState('');
  const [transferAgentId, setTransferAgentId] = useState('');
  const [transferReason, setTransferReason] = useState('');
  const [resolveSummary, setResolveSummary] = useState('');
  const [resolveCsat, setResolveCsat] = useState<number>(5);

  const loadTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        search: search || undefined,
      });
      setTickets(data);
      if (selectedTicket) {
        const refreshed = await api.getTicketDetail(selectedTicket.ticket_id);
        setSelectedTicket(refreshed);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTickets();
    api.getAgents().then(setAgents).catch(console.error);
  }, [statusFilter, priorityFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadTickets();
  };

  const handleSelectTicket = async (ticket: Ticket) => {
    try {
      const detail = await api.getTicketDetail(ticket.ticket_id);
      setSelectedTicket(detail);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createTicket({
        customer_id: newCustomerId,
        channel_id: newChannel,
        subject: newSubject,
        body: newBody,
      });
      setShowCreateModal(false);
      setNewSubject('');
      setNewBody('');
      loadTickets();
      onTicketUpdated();
    } catch (err: any) {
      alert(`Error creating ticket: ${err.message}`);
    }
  };

  const handleSendReply = async () => {
    if (!selectedTicket || !replyBody.trim()) return;
    try {
      await api.addMessage(selectedTicket.ticket_id, {
        sender_type: 'AGENT',
        sender_id: selectedTicket.assigned_agent_id || 'AGT-000001',
        body: replyBody,
      });
      setReplyBody('');
      const updated = await api.getTicketDetail(selectedTicket.ticket_id);
      setSelectedTicket(updated);
      onTicketUpdated();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleTransfer = async () => {
    if (!selectedTicket || !transferAgentId) return;
    try {
      await api.transferTicket(selectedTicket.ticket_id, {
        to_agent_id: transferAgentId,
        reason: transferReason || 'Reassigned to specialized staff',
      });
      setShowTransferModal(false);
      const updated = await api.getTicketDetail(selectedTicket.ticket_id);
      setSelectedTicket(updated);
      loadTickets();
      onTicketUpdated();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleEscalate = async () => {
    if (!selectedTicket) return;
    try {
      await api.escalateTicket(selectedTicket.ticket_id, {
        reason: 'Manual supervisor escalation requested',
      });
      const updated = await api.getTicketDetail(selectedTicket.ticket_id);
      setSelectedTicket(updated);
      loadTickets();
      onTicketUpdated();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleReopen = async () => {
    if (!selectedTicket) return;
    try {
      await api.reopenTicket(selectedTicket.ticket_id, {
        reason: 'Customer reported recurrence of issue',
      });
      const updated = await api.getTicketDetail(selectedTicket.ticket_id);
      setSelectedTicket(updated);
      loadTickets();
      onTicketUpdated();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleResolve = async () => {
    if (!selectedTicket) return;
    try {
      await api.resolveTicket(selectedTicket.ticket_id, {
        agent_id: selectedTicket.assigned_agent_id || 'AGT-000001',
        resolution_code: 'SOLVED',
        summary: resolveSummary || 'Issue verified and resolved successfully',
        csat_score: resolveCsat,
        csat_feedback: 'Satisfied with resolution time',
      });
      setShowResolveModal(false);
      const updated = await api.getTicketDetail(selectedTicket.ticket_id);
      setSelectedTicket(updated);
      loadTickets();
      onTicketUpdated();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const priorityBadge = (p: string) => {
    const styles: Record<string, string> = {
      P1: 'bg-red-100 text-red-700 border-red-300 font-bold',
      P2: 'bg-orange-100 text-orange-700 border-orange-300',
      P3: 'bg-blue-100 text-blue-700 border-blue-300',
      P4: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-[11px] font-mono border ${styles[p] || 'bg-slate-100'}`}>
        {p}
      </span>
    );
  };

  return (
    <div className="flex h-full overflow-hidden bg-slate-50">
      {/* Ticket List Column */}
      <div className={`flex flex-col border-r border-slate-200 bg-white transition-all ${selectedTicket ? 'w-1/2' : 'w-full'}`}>
        {/* Top Control Bar */}
        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <form onSubmit={handleSearch} className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by ticket ID or subject..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </form>

          <div className="flex items-center space-x-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium"
            >
              <option value="">All Statuses</option>
              <option value="NEW">NEW</option>
              <option value="ASSIGNED">ASSIGNED</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="QUEUED">QUEUED</option>
              <option value="ESCALATED">ESCALATED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="REOPENED">REOPENED</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium"
            >
              <option value="">All Priorities</option>
              <option value="P1">P1 Critical</option>
              <option value="P2">P2 High</option>
              <option value="P3">P3 Medium</option>
              <option value="P4">P4 Low</option>
            </select>

            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Ticket</span>
            </button>
          </div>
        </div>

        {/* Tickets Table / List */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading tickets...</div>
          ) : tickets.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">No tickets matching filter criteria.</div>
          ) : (
            tickets.map((t) => {
              const isSelected = selectedTicket?.ticket_id === t.ticket_id;
              return (
                <div
                  key={t.ticket_id}
                  onClick={() => handleSelectTicket(t)}
                  className={`p-3.5 cursor-pointer transition-colors ${
                    isSelected ? 'bg-blue-50/80 border-l-4 border-l-blue-600' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-slate-900">{t.ticket_id}</span>
                      {priorityBadge(t.priority)}
                      <span className="text-[11px] font-semibold text-slate-500 uppercase px-1.5 py-0.5 rounded bg-slate-100">
                        {t.channel_id}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400 uppercase">
                        [{t.language_code}]
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-slate-800 line-clamp-1">{t.subject}</p>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="font-mono text-slate-400">{t.customer_id}</span>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        t.status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-800' :
                        t.status === 'ESCALATED' ? 'bg-rose-100 text-rose-800' :
                        t.status === 'QUEUED' ? 'bg-amber-100 text-amber-800' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {t.status}
                      </span>
                      <span className="font-medium text-slate-600">
                        {t.assigned_agent_id ? t.assigned_agent_id : 'UNASSIGNED'}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Ticket Details & Conversation Drawer */}
      {selectedTicket && (
        <div className="w-1/2 flex flex-col bg-white overflow-hidden shadow-lg border-l border-slate-200">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-bold text-slate-900">{selectedTicket.ticket_id}</span>
                {priorityBadge(selectedTicket.priority)}
                <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-800 font-semibold">
                  {selectedTicket.status}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1 font-medium">{selectedTicket.subject}</p>
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                onClick={() => setShowTransferModal(true)}
                className="p-1.5 rounded hover:bg-slate-200 text-slate-600 text-xs flex items-center space-x-1"
                title="Transfer Ticket"
              >
                <ArrowRightLeft className="h-4 w-4" />
                <span className="text-[11px] font-medium">Transfer</span>
              </button>

              <button
                onClick={handleEscalate}
                className="p-1.5 rounded hover:bg-rose-100 text-rose-600 text-xs flex items-center space-x-1"
                title="Escalate Priority"
              >
                <AlertCircle className="h-4 w-4" />
                <span className="text-[11px] font-medium">Escalate</span>
              </button>

              {selectedTicket.status === 'RESOLVED' ? (
                <button
                  onClick={handleReopen}
                  className="p-1.5 rounded hover:bg-amber-100 text-amber-700 text-xs flex items-center space-x-1"
                  title="Reopen Ticket"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span className="text-[11px] font-medium">Reopen</span>
                </button>
              ) : (
                <button
                  onClick={() => setShowResolveModal(true)}
                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold flex items-center space-x-1"
                >
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>Resolve</span>
                </button>
              )}
            </div>
          </div>

          {/* Metadata Card */}
          <div className="p-3 bg-slate-100/70 border-b border-slate-200 grid grid-cols-4 gap-2 text-[11px]">
            <div>
              <span className="text-slate-400 block">Customer</span>
              <span className="font-semibold text-slate-800">{selectedTicket.customer?.name || selectedTicket.customer_id}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Assigned Agent</span>
              <span className="font-semibold text-blue-700">{selectedTicket.assigned_agent_id || 'QUEUED'}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Classified Intent</span>
              <span className="font-mono text-slate-800">{selectedTicket.intent_id}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Language</span>
              <span className="font-mono text-slate-800 uppercase">{selectedTicket.language_code}</span>
            </div>
          </div>

          {/* Conversation Thread */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
            {selectedTicket.messages?.map((msg) => {
              const isAgent = msg.sender_type === 'AGENT';
              return (
                <div key={msg.message_id} className={`flex flex-col ${isAgent ? 'items-end' : 'items-start'}`}>
                  <div className="flex items-center space-x-1 text-[10px] text-slate-400 mb-0.5">
                    <span className="font-semibold text-slate-600">{msg.sender_type} ({msg.sender_id})</span>
                    <span>•</span>
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className={`p-3 rounded-xl max-w-[85%] text-xs shadow-2xs leading-relaxed ${
                    isAgent ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
                  }`}>
                    {msg.body}
                  </div>
                </div>
              );
            })}

            {/* Resolution Card if resolved */}
            {selectedTicket.resolution && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs space-y-1 my-2">
                <div className="flex items-center justify-between text-emerald-800 font-semibold">
                  <span>Resolved ({selectedTicket.resolution.resolution_code})</span>
                  <div className="flex items-center text-amber-500">
                    {[...Array(selectedTicket.resolution.csat_score || 5)].map((_, i) => (
                      <Star key={i} className="h-3.5 w-3.5 fill-current" />
                    ))}
                  </div>
                </div>
                <p className="text-emerald-900">{selectedTicket.resolution.summary}</p>
                {selectedTicket.resolution.csat_feedback && (
                  <p className="text-[11px] text-emerald-700 italic">"{selectedTicket.resolution.csat_feedback}"</p>
                )}
              </div>
            )}
          </div>

          {/* Reply Input */}
          {selectedTicket.status !== 'RESOLVED' && (
            <div className="p-3 border-t border-slate-200 bg-white flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type agent response message..."
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendReply()}
                className="flex-1 px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <button
                onClick={handleSendReply}
                disabled={!replyBody.trim()}
                className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Create Ticket Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-800 mb-4">Ingest New Omnichannel Ticket</h3>
            <form onSubmit={handleCreateTicket} className="space-y-3.5">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Customer Identifier</label>
                <input
                  type="text"
                  value={newCustomerId}
                  onChange={(e) => setNewCustomerId(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Channel</label>
                <select
                  value={newChannel}
                  onChange={(e) => setNewChannel(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                >
                  <option value="email">Email</option>
                  <option value="chat">Live Chat</option>
                  <option value="phone">Voice / Phone</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Subject</label>
                <input
                  type="text"
                  placeholder="e.g. UPI Payment Failed at checkout"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Message Body</label>
                <textarea
                  rows={3}
                  placeholder="Customer description of the inquiry..."
                  value={newBody}
                  onChange={(e) => setNewBody(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
                >
                  Ingest & Route
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transfer Modal */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-sm w-full p-5 shadow-xl">
            <h3 className="text-sm font-bold text-slate-800 mb-3">Transfer Ticket</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Target Agent</label>
                <select
                  value={transferAgentId}
                  onChange={(e) => setTransferAgentId(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                >
                  <option value="">Select Agent...</option>
                  {agents.map((a) => (
                    <option key={a.agent_id} value={a.agent_id}>
                      {a.name} ({a.agent_id}) - Slots: {a.max_concurrency - a.current_active_tickets}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Reason</label>
                <input
                  type="text"
                  placeholder="Reason for transfer..."
                  value={transferReason}
                  onChange={(e) => setTransferReason(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setShowTransferModal(false)}
                  className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTransfer}
                  disabled={!transferAgentId}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50"
                >
                  Execute Transfer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {showResolveModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-xl">
            <h3 className="text-sm font-bold text-slate-800 mb-3">Resolve Ticket & Record CSAT</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Resolution Summary</label>
                <textarea
                  rows={2}
                  placeholder="Summary of how the issue was resolved..."
                  value={resolveSummary}
                  onChange={(e) => setResolveSummary(e.target.value)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Customer CSAT Rating (1 to 5)</label>
                <div className="flex space-x-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setResolveCsat(star)}
                      className={`p-1.5 rounded-lg border text-xs font-bold flex items-center space-x-1 ${
                        resolveCsat >= star ? 'bg-amber-50 border-amber-300 text-amber-600' : 'bg-slate-50 text-slate-400'
                      }`}
                    >
                      <Star className="h-4 w-4 fill-current" />
                      <span>{star}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setShowResolveModal(false)}
                  className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  onClick={handleResolve}
                  className="px-4 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold"
                >
                  Confirm Resolution
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
