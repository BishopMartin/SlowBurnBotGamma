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
  "w-full bg-[#262624] rounded-lg px-3 py-2 text-[#f0eee6] placeholder-[#73726c] outline-none border border-[#3d3d3a] focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] transition-colors";

const cardCls = "bg-[#1f1e1d] rounded-xl p-6 space-y-4 border border-[#3d3d3a]";

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
        <Link href="/dashboard/accounts" className="text-[#73726c] hover:text-[#f0eee6]">
          ← Accounts
        </Link>
        <h1 className="font-semibold text-[#f0eee6]">{account.name}</h1>
        <button
          onClick={() => handleAccountField({ enabled: !account.enabled })}
          className={`px-2 py-0.5 rounded-full transition-colors cursor-pointer ${
            account.enabled
              ? "bg-[#1a2e1a] text-green-400 hover:bg-red-950 hover:text-red-400"
              : "bg-[#262624] text-[#73726c] hover:bg-[#1a2e1a] hover:text-green-400"
          }`}
        >
          {account.enabled ? "Enabled" : "Disabled"}
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <label className="text-[#73726c]">Group</label>
          <input
            type="number"
            min={1}
            placeholder="—"
            value={account.group_number ?? ""}
            onChange={(e) =>
              setAccount((a) => a && { ...a, group_number: e.target.value ? +e.target.value : null })
            }
            onBlur={() => handleAccountField({ group_number: account.group_number })}
            className="w-20 bg-[#262624] rounded-lg px-3 py-1 text-[#f0eee6] placeholder-[#73726c] outline-none border border-[#3d3d3a] focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] transition-colors"
          />
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Schedule */}
        <div className={cardCls} style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <h2 className="font-medium text-[#f0eee6]">Schedule</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[#73726c] mb-1">Days</label>
              <input
                type="text"
                placeholder="e.g. daily"
                value={settings.schedule_days ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_days: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Max runs / day</label>
              <input
                type="number"
                min={1}
                value={settings.max_runs_per_day ?? 1}
                onChange={(e) => setSettings((s) => ({ ...s, max_runs_per_day: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Start time</label>
              <input
                type="time"
                value={settings.schedule_start ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_start: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">End time</label>
              <input
                type="time"
                value={settings.schedule_end ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_end: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Delay base (min)</label>
              <input
                type="number"
                min={0}
                value={settings.delay_base_minutes ?? 60}
                onChange={(e) => setSettings((s) => ({ ...s, delay_base_minutes: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Delay random (min)</label>
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
        <div className={cardCls} style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <h2 className="font-medium text-[#f0eee6]">Actions</h2>
          <div className="grid grid-cols-[3rem_2.5rem_1fr_1fr_4rem_4rem] gap-2 text-[#73726c] px-1">
            <span></span>
            <span className="text-center">On</span>
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
              <span className="text-[#73726c]">{ACTION_LABELS[i]}</span>
              <div className="flex justify-center">
                <input
                  type="checkbox"
                  checked={action.enabled}
                  onChange={(e) => updateAction(i, { enabled: e.target.checked })}
                  className="w-4 h-4 accent-[#d97757] cursor-pointer"
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
        <div className={cardCls} style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <h2 className="font-medium text-[#f0eee6]">Follow Settings</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[#73726c] mb-1">Unfollow after (days)</label>
              <input
                type="number"
                min={1}
                value={settings.unfollow_days ?? 30}
                onChange={(e) => setSettings((s) => ({ ...s, unfollow_days: +e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">List tab name</label>
              <input
                type="text"
                placeholder="e.g. list-MainLineBars"
                value={settings.list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, list_tab: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Account group (comma-separated)</label>
              <input
                type="text"
                placeholder="e.g. account1, account2"
                value={settings.account_group ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_group: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-[#73726c] mb-1">Account list tab</label>
              <input
                type="text"
                placeholder="tab name"
                value={settings.account_list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_list_tab: e.target.value || null }))}
                className={inputCls}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-[#73726c] mb-1">Topics (comma-separated)</label>
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
            className="bg-[#c6613f] hover:bg-[#d97757] disabled:opacity-50 rounded-lg px-4 py-2 font-medium text-[#f0eee6] transition-colors"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
          {msg && <span className="text-green-400">{msg}</span>}
        </div>
      </form>
    </div>
  );
}
