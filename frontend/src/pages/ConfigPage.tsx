import React, { useState, useEffect } from 'react';
import { Settings, Save, ShieldCheck, CheckCircle2, Sliders } from 'lucide-react';
import { api } from '../services/api';

export const ConfigPage: React.FC = () => {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  // Editable weights
  const [weightSkill, setWeightSkill] = useState<number>(0.35);
  const [weightLang, setWeightLang] = useState<number>(0.25);
  const [weightCap, setWeightCap] = useState<number>(0.25);
  const [weightExp, setWeightExp] = useState<number>(0.15);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig();
      setConfig(data);
      if (data.routing_weights) {
        setWeightSkill(data.routing_weights.skill);
        setWeightLang(data.routing_weights.language);
        setWeightCap(data.routing_weights.capacity);
        setWeightExp(data.routing_weights.experience);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const handleSaveWeights = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.updateWeights({
        weight_skill: weightSkill,
        weight_language: weightLang,
        weight_capacity: weightCap,
        weight_experience: weightExp,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
      loadConfig();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  const totalWeight = Math.round((weightSkill + weightLang + weightCap + weightExp) * 100);

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div>
        <h2 className="text-base font-bold text-slate-900">System Configuration & Policy Center</h2>
        <p className="text-xs text-slate-500">
          Parameterize multi-factor scoring weights, view SLA deadlines, and audit deterministic safety invariants
        </p>
      </div>

      {loading ? (
        <div className="p-16 text-center text-xs text-slate-400">Loading system configurations...</div>
      ) : config ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Routing Scoring Weights Form */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Sliders className="h-5 w-5 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-800">Dynamic Multi-Factor Routing Weights</h3>
              </div>
              <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded ${
                totalWeight === 100 ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
              }`}>
                Sum: {totalWeight}%
              </span>
            </div>

            <form onSubmit={handleSaveWeights} className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Mandatory Skill Match Weight (S)</span>
                  <span className="font-mono">{Math.round(weightSkill * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={weightSkill}
                  onChange={(e) => setWeightSkill(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Language Fluency Weight (L)</span>
                  <span className="font-mono">{Math.round(weightLang * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={weightLang}
                  onChange={(e) => setWeightLang(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Available Concurrency Capacity Weight (C)</span>
                  <span className="font-mono">{Math.round(weightCap * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={weightCap}
                  onChange={(e) => setWeightCap(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Historical Performance / Experience Weight (E)</span>
                  <span className="font-mono">{Math.round(weightExp * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={weightExp}
                  onChange={(e) => setWeightExp(parseFloat(e.target.value))}
                  className="w-full accent-blue-600 cursor-pointer"
                />
              </div>

              <div className="pt-2 flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-mono">Changes persist live to backend memory</span>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  <span>{saving ? 'Updating...' : 'Save Routing Policy'}</span>
                </button>
              </div>

              {savedSuccess && (
                <div className="p-2.5 bg-emerald-50 text-emerald-800 rounded-lg text-xs font-semibold flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span>Routing policy updated successfully! All future assignments will reflect new weights.</span>
                </div>
              )}
            </form>
          </div>

          {/* Safety Rules & Invariants */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-6 space-y-4">
            <div className="flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-emerald-600" />
              <h3 className="text-sm font-bold text-slate-800">Hard Safety Invariant Rules</h3>
            </div>

            <div className="divide-y divide-slate-100 text-xs">
              {config.safety_rules?.map((rule: any) => (
                <div key={rule.id} className="py-2.5 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">{rule.name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 font-mono">
                      FORCED {rule.priority}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Rule ID: <span className="font-mono">{rule.id}</span> • Critical Invariant: <span className="font-semibold text-rose-600">CANNOT BE DOWNGRADED</span>
                  </p>
                </div>
              ))}
            </div>

            {/* SLA Policies */}
            <div className="pt-4 border-t border-slate-200">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">SLA Default Targets</h4>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">P1 CRITICAL</span>
                  <span>Resp: 5m | Res: 60m</span>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">P2 HIGH</span>
                  <span>Resp: 15m | Res: 240m</span>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">P3 MEDIUM</span>
                  <span>Resp: 60m | Res: 480m</span>
                </div>
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">P4 LOW</span>
                  <span>Resp: 240m | Res: 1440m</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
