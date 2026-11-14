import React, { useState } from 'react';
import {
  Mail, MessageSquare, PhoneCall, Send, Sparkles, CheckCircle2,
  Clock, ShieldAlert, User, ArrowRight
} from 'lucide-react';
import { api } from '../services/api';

export const SimulatorPage: React.FC = () => {
  const [activeChannel, setActiveChannel] = useState<'email' | 'chat' | 'phone'>('chat');

  // Customer Email State
  const [emailSender, setEmailSender] = useState('john.smith@acmecorp.com');
  const [emailSubject, setEmailSubject] = useState('Payment failed at checkout UPI error 504');
  const [emailBody, setEmailBody] = useState('Hello support team, my payment was debited from my bank account but your checkout showed an error. Please verify and credit order.');

  // Website Chatbot State
  const [chatCustomerId, setChatCustomerId] = useState('CUS-000042');
  const [chatMessage, setChatMessage] = useState('Nenu payment chesanu kani failed ani vachindi sahayam cheyandi.');

  // Phone Call State
  const [callerPhone, setCallerPhone] = useState('+91 98765 43210');
  const [callerName, setCallerName] = useState('Sneha Rao');
  const [ivrSelection, setIvrSelection] = useState('Option 1: Emergency & Fraud');
  const [voiceTranscript, setVoiceTranscript] = useState('Customer on call: Urgent! My account credentials were stolen and unauthorized transactions are happening right now!');

  // Submission & Result State
  const [loading, setLoading] = useState(false);
  const [ingestedResult, setIngestedResult] = useState<any>(null);
  const [routingResult, setRoutingResult] = useState<any>(null);

  // Quick Presets
  const setPreset = (channel: 'email' | 'chat' | 'phone', subject: string, body: string) => {
    setActiveChannel(channel);
    if (channel === 'email') {
      setEmailSubject(subject);
      setEmailBody(body);
    } else if (channel === 'chat') {
      setChatMessage(body);
    } else if (channel === 'phone') {
      setVoiceTranscript(body);
    }
  };

  const handleSimulateIngest = async () => {
    setLoading(true);
    setIngestedResult(null);
    setRoutingResult(null);

    let customerId = 'CUS-000001';
    let subject = '';
    let body = '';

    if (activeChannel === 'email') {
      customerId = 'CUS-000010';
      subject = emailSubject;
      body = emailBody;
    } else if (activeChannel === 'chat') {
      customerId = chatCustomerId;
      subject = `Live Website Chat: ${chatMessage.slice(0, 45)}...`;
      body = chatMessage;
    } else if (activeChannel === 'phone') {
      customerId = 'CUS-000025';
      subject = `Inbound Phone Call [${ivrSelection}]: ${callerName}`;
      body = `Telephony Transcript from ${callerPhone}: ${voiceTranscript}`;
    }

    try {
      // 1. Ingest Ticket into backend
      const ticket = await api.createTicket({
        customer_id: customerId,
        channel_id: activeChannel,
        subject: subject,
        body: body,
      });
      setIngestedResult(ticket);

      // 2. Fetch the explainable routing evaluation
      const evalData = await api.evaluateRouting(ticket.ticket_id);
      setRoutingResult(evalData);
    } catch (err: any) {
      alert(`Ingestion error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div>
        <h2 className="text-base font-bold text-slate-900">Omnichannel Ingestion & Query Simulator</h2>
        <p className="text-xs text-slate-500">
          Test in real-time how the platform ingests, classifies, and routes customer queries arriving from Email, Website Chatbot, or Inbound Phone Calls.
        </p>
      </div>

      {/* Preset Badges for One-Click Testing */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
          One-Click Test Scenarios (Try These)
        </span>
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            onClick={() => setPreset('chat', 'UPI Payment Error', 'Nenu payment chesanu kani failed ani vachindi sahayam cheyandi.')}
            className="px-2.5 py-1 rounded-lg bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100 font-medium flex items-center space-x-1"
          >
            <span>💬 Live Chat (Telugu Payment Dispute)</span>
          </button>

          <button
            onClick={() => setPreset('phone', 'Inbound Call: Account Compromise', 'Urgent! My account credentials were stolen and unauthorized transactions are happening right now!')}
            className="px-2.5 py-1 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 font-medium flex items-center space-x-1"
          >
            <span>📞 Phone Call (Emergency P1 Security Breach)</span>
          </button>

          <button
            onClick={() => setPreset('email', 'Invoice Tax Inquiry', 'Dear team, could you please provide a revised GST invoice for subscription renewal order #48192?')}
            className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 font-medium flex items-center space-x-1"
          >
            <span>📧 Customer Email (Routine Billing Query)</span>
          </button>

          <button
            onClick={() => setPreset('chat', 'Hindi Technical Bug', 'Mera dashboard login nahi ho raha hai OTP nahi aaya please madad kijiye.')}
            className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 font-medium flex items-center space-x-1"
          >
            <span>💬 Website Chat (Hindi Auth / OTP Bug)</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Channel Simulator UI */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
          {/* Channel Selector Tabs */}
          <div className="grid grid-cols-3 border-b border-slate-200 bg-slate-50 text-xs font-semibold">
            <button
              onClick={() => setActiveChannel('chat')}
              className={`p-3 flex items-center justify-center space-x-2 border-b-2 transition-colors ${
                activeChannel === 'chat'
                  ? 'border-blue-600 text-blue-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <MessageSquare className="h-4 w-4" />
              <span>Website Chatbot</span>
            </button>

            <button
              onClick={() => setActiveChannel('email')}
              className={`p-3 flex items-center justify-center space-x-2 border-b-2 transition-colors ${
                activeChannel === 'email'
                  ? 'border-blue-600 text-blue-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Mail className="h-4 w-4" />
              <span>Customer Email</span>
            </button>

            <button
              onClick={() => setActiveChannel('phone')}
              className={`p-3 flex items-center justify-center space-x-2 border-b-2 transition-colors ${
                activeChannel === 'phone'
                  ? 'border-blue-600 text-blue-600 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <PhoneCall className="h-4 w-4" />
              <span>Phone / Voice Call</span>
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-5 flex-1 space-y-4">
            {activeChannel === 'chat' && (
              <div className="space-y-3">
                <div className="p-3 bg-cyan-50 border border-cyan-200 rounded-lg text-xs text-cyan-900 flex items-center justify-between">
                  <span>Channel: <strong>Live Website Chat Widget</strong></span>
                  <span className="font-mono bg-cyan-100 text-cyan-800 px-2 py-0.5 rounded text-[11px]">SLA Multiplier: 0.5x</span>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Customer Session ID</label>
                  <input
                    type="text"
                    value={chatCustomerId}
                    onChange={(e) => setChatCustomerId(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Visitor Message in Website Chat</label>
                  <textarea
                    rows={4}
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    placeholder="Visitor message in website chat bubble..."
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {activeChannel === 'email' && (
              <div className="space-y-3">
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-xs text-indigo-900 flex items-center justify-between">
                  <span>Channel: <strong>Inbound Email Server (IMAP / Webhook)</strong></span>
                  <span className="font-mono bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded text-[11px]">SLA Multiplier: 1.0x (Async)</span>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Sender Email</label>
                  <input
                    type="text"
                    value={emailSender}
                    onChange={(e) => setEmailSender(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Email Subject</label>
                  <input
                    type="text"
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg font-medium"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Email Message Body</label>
                  <textarea
                    rows={4}
                    value={emailBody}
                    onChange={(e) => setEmailBody(e.target.value)}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {activeChannel === 'phone' && (
              <div className="space-y-3">
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-900 flex items-center justify-between">
                  <span>Channel: <strong>Inbound Voice Call (Telephony / IVR Webhook)</strong></span>
                  <span className="font-mono bg-rose-100 text-rose-800 px-2 py-0.5 rounded text-[11px]">SLA Multiplier: 0.2x (1 min target)</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">Caller Phone Number</label>
                    <input
                      type="text"
                      value={callerPhone}
                      onChange={(e) => setCallerPhone(e.target.value)}
                      className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">IVR Keypad Routing</label>
                    <select
                      value={ivrSelection}
                      onChange={(e) => setIvrSelection(e.target.value)}
                      className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                    >
                      <option value="Option 1: Emergency & Fraud">Option 1: Emergency & Fraud</option>
                      <option value="Option 2: Billing & Payments">Option 2: Billing & Payments</option>
                      <option value="Option 3: General Support">Option 3: General Support</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Speech-to-Text Live Call Transcript</label>
                  <textarea
                    rows={3}
                    value={voiceTranscript}
                    onChange={(e) => setVoiceTranscript(e.target.value)}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            <button
              onClick={handleSimulateIngest}
              disabled={loading}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              <span>{loading ? 'Ingesting, Classifying & Routing...' : `Simulate Inbound ${activeChannel.toUpperCase()} Event`}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Real-Time Ingestion & Routing Result */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide flex items-center space-x-1.5">
                <Sparkles className="h-4 w-4 text-amber-500" />
                <span>Live System Ingestion & Dispatch Result</span>
              </h3>
              {ingestedResult && (
                <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                  {ingestedResult.ticket_id}
                </span>
              )}
            </div>

            {!ingestedResult ? (
              <div className="py-20 text-center text-xs text-slate-400 space-y-2">
                <div className="h-10 w-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                  <ArrowRight className="h-5 w-5" />
                </div>
                <p className="font-medium text-slate-600">No query simulated yet.</p>
                <p className="text-[11px] text-slate-400">Select a channel on the left or click a one-click preset to see the system ingest and route in real time.</p>
              </div>
            ) : (
              <div className="space-y-4 text-xs">
                {/* Classification Badges */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Detected Intent</span>
                    <span className="font-mono font-bold text-slate-800">{ingestedResult.intent_id}</span>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Language Detected</span>
                    <span className="font-mono font-bold text-slate-800 uppercase">
                      {ingestedResult.language_code === 'te' ? 'Telugu (te)' :
                       ingestedResult.language_code === 'hi' ? 'Hindi (hi)' :
                       ingestedResult.language_code === 'ta' ? 'Tamil (ta)' :
                       ingestedResult.language_code === 'kn' ? 'Kannada (kn)' : 'English (en)'}
                    </span>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Assigned Priority</span>
                    <span className={`font-mono font-bold ${ingestedResult.priority === 'P1' ? 'text-red-600' : 'text-blue-600'}`}>
                      {ingestedResult.priority} {ingestedResult.priority === 'P1' && '(Safety Rule Active)'}
                    </span>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Ingestion Channel</span>
                    <span className="font-semibold text-slate-800 uppercase">{ingestedResult.channel_id}</span>
                  </div>
                </div>

                {/* Routing Outcome */}
                <div className="p-3.5 bg-emerald-50/80 border border-emerald-200 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between text-emerald-800 font-bold">
                    <span>Assigned Support Agent</span>
                    <span className="font-mono text-xs">{ingestedResult.assigned_agent_id || 'QUEUED (No Agent Free)'}</span>
                  </div>
                  {routingResult && (
                    <p className="text-emerald-950 text-[11px] leading-relaxed">
                      {routingResult.explanation}
                    </p>
                  )}
                </div>

                {/* Candidate Breakdown */}
                {routingResult && routingResult.candidate_scores?.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Candidate Scoring Breakdown
                    </span>
                    <div className="space-y-1">
                      {routingResult.candidate_scores.slice(0, 3).map((cand: any, idx: number) => (
                        <div key={cand.agent_id} className="flex items-center justify-between p-2 bg-slate-50 rounded border border-slate-100 text-[11px]">
                          <span className="font-medium text-slate-800">
                            #{idx + 1} {cand.agent_name} ({cand.agent_id})
                          </span>
                          <span className="font-mono font-bold text-blue-600">
                            Score: {cand.total_score.toFixed(1)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Unified REST Endpoint: <code className="font-mono">POST /api/v1/tickets</code></span>
            <span>Deterministic Seed: <code className="font-mono">20261022</code></span>
          </div>
        </div>
      </div>
    </div>
  );
};
