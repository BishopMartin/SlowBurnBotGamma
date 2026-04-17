"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getAccounts,
  getAccountSettings,
  saveAccountSettings,
  updateAccount,
  Account,
  AccountSettings,
  ActionBlock,
} from "@/lib/api";

const ACTION_LABELS = ["1st", "2nd", "3rd", "4th"] as const;

const DEFAULT_ACTION: ActionBlock = {
  enabled: false,
  type: "",
  target: "",
  fixed_count: 0,
  variable_count: 0,
};

function pad4(actions: ActionBlock[] | null | undefined): ActionBlock[] {
  const base = actions ?? [];
  return [0, 1, 2, 3].map((i) => base[i] ?? { ...DEFAULT_ACTION });
}

const inputCls =
  "w-full bg-gray-800 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-blue-500";

export default function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [settings, setSettings] = useState<Partial<AccountSettings>>({});
  const [actions, setActions] = useState<ActionBlock[]>(pad4(null));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getAccounts().then((list) => {
      const found = list.find((a) => a.id === id) ?? null;
      if (!found) { router.push("/dashboard/accounts"); return; }
      setAccount(found);
    });
    getAccountSettings(id)
      .then((s) => {
        setSettings(s);
        setActions(pad4(s.actions));
      })
      .catch(() => {});
  }, [id, router]);

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    try {
      await saveAccountSettings(id, { ...settings, actions });
      setMsg("Saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleEnabled() {
    if (!account) return;
    const updated = await updateAccount(id, { enabled: !account.enabled });
    setAccount(updated);
  }

  function updateAction(index: number, patch: Partial<ActionBlock>) {
    setActions((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)));
  }

  async function handleAccountField(patch: Partial<Account>) {
    const updated = await updateAccount(id, patch).catch(() => null);
    if (updated) setAccount(updated);
  }

  if (!account) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/dashboard/accounts" className="text-gray-400 hover:text-white text-sm">
          ← Accounts
        </Link>
        <h1 className="text-xl font-semibold">{account.name}</h1>
        <button
          onClick={toggleEnabled}
          className={`text-xs px-2 py-0.5 rounded-full transition-colors cursor-pointer ${
            account.enabled
              ? "bg-green-900 text-green-300 hover:bg-red-900 hover:text-red-300"
              : "bg-gray-800 text-gray-400 hover:bg-green-900 hover:text-green-300"
          }`}
        >
          {account.enabled ? "Enabled" : "Disabled"}
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-xs text-gray-400">Group</label>
          <input
            type="number"
            min={1}
            placeholder="—"
            value={account.group_number ?? ""}
            onChange={(e) =>
              setAccount((a) => a && { ...a, group_number: e.target.value ? +e.target.value : null })
            }
            onBlur={() => handleAccountField({ group_number: account.group_number })}
            className="w-20 bg-gray-800 rounded-lg px-3 py-1 text-sm text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Proxy */}
        <div className="bg-gray-900 rounded-xl p-6 space-y-4">
          <h2 className="font-medium">Proxy</h2>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="proxy_enabled"
              checked={account.proxy_enabled}
              onChange={() => handleAccountField({ proxy_enabled: !account.proxy_enabled })}
              className="w-4 h-4 accent-blue-500 cursor-pointer"
            />
            <label htmlFor="proxy_enabled" className="text-sm text-gray-300 cursor-pointer">
              Enabled
            </label>
          </div>
          <div className="max-w-xs">
            <label className="block text-xs text-gray-400 mb-1">Type</label>
            <input
              type="text"
              placeholder="e.g. none"
              value={account.proxy_type ?? ""}
              onChange={(e) =>
                setAccount((a) => a && { ...a, proxy_type: e.target.value || null })
              }
              onBlur={() => handleAccountField({ proxy_type: account.proxy_type })}
              className={inputCls}
            />
          </div>
        </div>

        {/* Schedule */}
        <div className="bg-gray-900 rounded-xl p-6 space-y-4">
          <h2 className="font-medium">Schedule</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Days</label>
              <input
                type="text"
                placeholder="e.g. daily"
                value={settings.schedule_days ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_days: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Max runs / day</label>
              <input
                type="number"
                min={1}
                value={settings.max_runs_per_day ?? 1}
                onChange={(e) => setSettings((s) => ({ ...s, max_runs_per_day: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Start time</label>
              <input
                type="time"
                value={settings.schedule_start ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_start: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">End time</label>
              <input
                type="time"
                value={settings.schedule_end ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_end: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Delay base (min)</label>
              <input
                type="number"
                min={0}
                value={settings.delay_base_minutes ?? 60}
                onChange={(e) => setSettings((s) => ({ ...s, delay_base_minutes: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Delay random (min)</label>
              <input
                type="number"
                min={0}
                value={settings.delay_random_minutes ?? 0}
                onChange={(e) => setSettings((s) => ({ ...s, delay_random_minutes: +e.target.value }))}
                className={inputCls}
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-gray-900 rounded-xl p-6 space-y-3">
          <h2 className="font-medium">Actions</h2>
          {/* Column headers */}
          <div className="grid grid-cols-[3rem_2.5rem_1fr_1fr_4rem_4rem] gap-2 text-xs text-gray-500 px-1">
            <span></span>
            <span>On</span>
            <span>Type</span>
            <span>Target</span>
            <span className="text-center">#</span>
            <span className="text-center">?</span>
          </div>
          {actions.map((action, i) => (
            <div
              key={i}
              className="grid grid-cols-[3rem_2.5rem_1fr_1fr_4rem_4rem] gap-2 items-center"
            >
              <span className="text-xs text-gray-500">{ACTION_LABELS[i]}</span>
              <div className="flex justify-center">
                <input
                  type="checkbox"
                  checked={action.enabled}
                  onChange={(e) => updateAction(i, { enabled: e.target.checked })}
                  className="w-4 h-4 accent-blue-500 cursor-pointer"
                />
              </div>
              <input
                type="text"
                placeholder="e.g. follow"
                value={action.type}
                onChange={(e) => updateAction(i, { type: e.target.value })}
                className={inputCls}
              />
              <input
                type="text"
                placeholder="username / tag"
                value={action.target}
                onChange={(e) => updateAction(i, { target: e.target.value })}
                className={inputCls}
              />
              <input
                type="number"
                min={0}
                value={action.fixed_count}
                onChange={(e) => updateAction(i, { fixed_count: +e.target.value })}
                className={inputCls}
              />
              <input
                type="number"
                min={0}
                value={action.variable_count}
                onChange={(e) => updateAction(i, { variable_count: +e.target.value })}
                className={inputCls}
              />
            </div>
          ))}
        </div>

        {/* Follow Settings */}
        <div className="bg-gray-900 rounded-xl p-6 space-y-4">
          <h2 className="font-medium">Follow Settings</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Unfollow after (days)</label>
              <input
                type="number"
                min={1}
                value={settings.unfollow_days ?? 30}
                onChange={(e) => setSettings((s) => ({ ...s, unfollow_days: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">List tab name</label>
              <input
                type="text"
                placeholder="e.g. list-MainLineBars"
                value={settings.list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, list_tab: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Account group (comma-separated)</label>
              <input
                type="text"
                placeholder="e.g. account1, account2"
                value={settings.account_group ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_group: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Account list tab</label>
              <input
                type="text"
                placeholder="tab name"
                value={settings.account_list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_list_tab: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-400 mb-1">Topics (comma-separated)</label>
              <input
                type="text"
                value={settings.topics ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, topics: e.target.value || null }))}
                className={inputCls}
              />
            </div>
          </div>
        </div>

        {/* Save */}
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
          {msg && <span className="text-sm text-green-400">{msg}</span>}
        </div>
      </form>
    </div>
  );
}
