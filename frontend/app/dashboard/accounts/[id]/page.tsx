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
} from "@/lib/api";

export default function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [settings, setSettings] = useState<Partial<AccountSettings>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getAccounts().then((list) => {
      const found = list.find((a) => a.id === id) ?? null;
      if (!found) { router.push("/dashboard/accounts"); return; }
      setAccount(found);
    });
    getAccountSettings(id).then(setSettings).catch(() => {});
  }, [id, router]);

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    try {
      await saveAccountSettings(id, settings);
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

  if (!account) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
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
      </div>

      <form onSubmit={handleSaveSettings} className="bg-gray-900 rounded-xl p-6 space-y-5">
        <h2 className="font-medium">Schedule</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Days</label>
            <input
              type="text"
              placeholder="e.g. daily"
              value={settings.schedule_days ?? ""}
              onChange={(e) => setSettings((s) => ({ ...s, schedule_days: e.target.value }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Max runs / day</label>
            <input
              type="number"
              min={1}
              value={settings.max_runs_per_day ?? 1}
              onChange={(e) => setSettings((s) => ({ ...s, max_runs_per_day: +e.target.value }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Start time</label>
            <input
              type="time"
              value={settings.schedule_start ?? ""}
              onChange={(e) => setSettings((s) => ({ ...s, schedule_start: e.target.value || null }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">End time</label>
            <input
              type="time"
              value={settings.schedule_end ?? ""}
              onChange={(e) => setSettings((s) => ({ ...s, schedule_end: e.target.value || null }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Delay base (min)</label>
            <input
              type="number"
              min={0}
              value={settings.delay_base_minutes ?? 60}
              onChange={(e) => setSettings((s) => ({ ...s, delay_base_minutes: +e.target.value }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Delay random (min)</label>
            <input
              type="number"
              min={0}
              value={settings.delay_random_minutes ?? 0}
              onChange={(e) => setSettings((s) => ({ ...s, delay_random_minutes: +e.target.value }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Unfollow after (days)</label>
            <input
              type="number"
              min={1}
              value={settings.unfollow_days ?? 30}
              onChange={(e) => setSettings((s) => ({ ...s, unfollow_days: +e.target.value }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Topics (comma-separated)</label>
            <input
              type="text"
              value={settings.topics ?? ""}
              onChange={(e) => setSettings((s) => ({ ...s, topics: e.target.value || null }))}
              className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

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
