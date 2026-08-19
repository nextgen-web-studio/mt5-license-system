'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { Gift, Save, ShieldAlert, CheckCircle2, Clock, Users } from 'lucide-react';
import api from '@/lib/api';
import ConfirmModal from '@/components/ui/ConfirmModal';

interface TrialSettings {
  enabled: boolean;
  duration_days: number;
  max_trials_per_month: number;
  allow_existing_customers: boolean;
  trial_plan_name: string;
}

export default function TrialAdminPage() {
  const queryClient = useQueryClient();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);

  const [settings, setSettings] = useState<TrialSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  // Manual Grant State
  const [grantTg, setGrantTg] = useState('');
  const [grantMt5, setGrantMt5] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const { data } = await api.get('/api/v1/trials/settings');
      setSettings(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg('');
    try {
      await api.put('/api/v1/trials/settings', settings);
      setMsg('Settings saved successfully!');
      setTimeout(() => setMsg(''), 3000);
    } catch (e) {
      console.error(e);
      setMsg('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-white">Loading settings...</div>;
  if (!settings) return <div className="text-red-500">Failed to load settings.</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Gift className="text-purple-500" size={32} />
            Free Trial Configuration
          </h1>
          <p className="text-neutral-400 mt-1">Manage rules, limits, and manual grants for the EA Trial system.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Settings Card */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
            <ShieldAlert size={20} className="text-blue-400" />
            Global Settings
          </h2>
          
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-white block">Trial Status</label>
                <span className="text-xs text-neutral-400">Enable or disable trials globally</span>
              </div>
              <button
                onClick={() => setSettings({ ...settings, enabled: !settings.enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.enabled ? 'bg-green-500' : 'bg-neutral-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div>
              <label className="text-sm font-medium text-white block mb-1">Duration (Days)</label>
              <input 
                type="number" 
                disabled={!settings.enabled}
                value={settings.duration_days}
                onChange={e => setSettings({...settings, duration_days: parseInt(e.target.value)})}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" 
              />
            </div>

            <div>
              <label className="text-sm font-medium text-white block mb-1">Max Trials Per Month</label>
              <input 
                type="number" 
                disabled={!settings.enabled}
                value={settings.max_trials_per_month}
                onChange={e => setSettings({...settings, max_trials_per_month: parseInt(e.target.value)})}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" 
              />
            </div>

            <div>
              <label className="text-sm font-medium text-white block mb-1">Trial Plan Name (For Compiler)</label>
              <input 
                type="text" 
                disabled={!settings.enabled}
                value={settings.trial_plan_name}
                onChange={e => setSettings({...settings, trial_plan_name: e.target.value})}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" 
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <div>
                <label className="text-sm font-medium text-white block">Allow Existing Customers</label>
                <span className="text-xs text-neutral-400">Can paid users claim trials?</span>
              </div>
              <button
                disabled={!settings.enabled}
                onClick={() => setSettings({ ...settings, allow_existing_customers: !settings.allow_existing_customers })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  settings.allow_existing_customers ? 'bg-blue-500' : 'bg-neutral-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.allow_existing_customers ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="pt-4 border-t border-neutral-800">
              <button 
                onClick={handleSave}
                disabled={saving}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                <Save size={18} />
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
              {msg && <p className="text-green-400 text-sm mt-2 text-center">{msg}</p>}
            </div>
          </div>
        </div>

        {/* Manual Grant Card */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
            <Gift size={20} className="text-green-400" />
            Manual Trial Grant
          </h2>
          <p className="text-sm text-neutral-400 mb-6">
            Bypass monthly limits to manually grant a trial for customer support purposes.
          </p>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-white block mb-1">Telegram User ID</label>
              <input 
                type="text" 
                placeholder="e.g. 123456789"
                value={grantTg}
                onChange={e => setGrantTg(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500" 
              />
            </div>
            <div>
              <label className="text-sm font-medium text-white block mb-1">MT5 ID</label>
              <input 
                type="text" 
                placeholder="e.g. 5312698"
                value={grantMt5}
                onChange={e => setGrantMt5(e.target.value)}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500" 
              />
            </div>
            
            <button className="w-full bg-neutral-800 hover:bg-neutral-700 text-white font-medium py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors mt-4">
              <CheckCircle2 size={18} />
              Grant Trial
            </button>
          </div>
        </div>

        {/* Reset Trial Data Card */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 md:col-span-2">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <Users size={20} className="text-red-400" />
            Reset Trial Limits
          </h2>
          <p className="text-neutral-400 text-sm mb-4">
            If a user has exhausted their free trial limit (e.g. for testing purposes), you can completely wipe their trial history here so they can claim a trial again.
          </p>
          <div className="flex gap-3">
            <input 
              type="text" 
              placeholder="Enter User's Telegram ID"
              value={grantTg}
              onChange={e => setGrantTg(e.target.value)}
              className="flex-1 bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-red-500"
            />
            <button 
              onClick={() => { if(!grantTg) return; setDeletingId(grantTg); setDeleteModalOpen(true); }}
              className="bg-red-500/10 text-red-500 border border-red-500/50 px-6 py-2 rounded-lg font-medium hover:bg-red-500/20 transition-colors"
            >
              Reset History
            </button>
          </div>
        </div>
      </div>
      
      {/* Stats/Logs section placeholder */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 mt-6">
        <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
          <Users size={20} className="text-indigo-400" />
          Active Trials
        </h2>
        <div className="bg-neutral-950 rounded-lg border border-neutral-800 p-8 text-center">
          <Clock size={40} className="text-neutral-600 mx-auto mb-3" />
          <p className="text-neutral-400">Trial statistics and active licenses will appear here.</p>
        </div>
      </div>
    
      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Reset Trial History"
        message="Are you sure you want to permanently delete this user trial history? They will be able to claim a free trial immediately."
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={async () => {
          if(!deletingId) return;
          try {
            await api.delete(`/api/v1/trials/admin/reset/${deletingId}`);
            window.location.reload();
          } catch(e) {
            alert('Failed to delete. Make sure your API is fully deployed!');
          }
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}
      />
    
</div>
  );
}
