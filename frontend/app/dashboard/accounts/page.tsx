"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAccounts,
  getAccountSettings,
  createAccount,
  deleteAccount,
  updateAccount,
  Account,
  AccountSettings,
} from "@/lib/api";

function scheduleLabel(s: AccountSettings | undefined): string {
  if (!s) return "—";
  const parts: string[] = [];
  if (s.schedule_days) parts.push(s.schedule_days);
  if (s.schedule_start || s.schedule_end) {
    parts.push(`${s.schedule_start ?? "?"} – ${s.schedule_end ?? "?"}`);
  }
  if (s.max_runs_per_day) parts.push(`×${s.max_runs_per_day}/day`);
  return parts.length ? parts.join("  ") : "—";
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [settingsMap, setSettingsMap] = useState<Record<string, AccountSettings>>({});
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    const data = await getAccounts().catch(() => []);
    setAccounts(data);
    const entries = await Promise.all(
      data.map((a) =>
        getAccountSettings(a.id)
          .then((s) => [a.id, s] as const)
          .catch(() => null)
      )
    );
    setSettingsMap(
      Object.fromEntries(entries.filter((e): e is [string, AccountSettings] => e !== null))
    );
  }

  useEffect(() => { load(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    setError("");
    try {
      await createAccount({ name: newName.trim() });
      setNewName("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create account.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete account "${name}"?`)) return;
    await deleteAccount(id).catch(() => {});
    await load();
  }

  async function handleToggleEnabled(account: Account) {
    const updated = await updateAccount(account.id, { enabled: !account.enabled }).catch(() => null);
    if (updated) setAccounts((prev) => prev.map((a) => (a.id === account.id ? updated : a)));
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Accounts</h1>

      {accounts.length === 0 ? (
        <div className="bg-gray-900 rounded-xl p-8 text-center text-gray-400 text-sm">
          No accounts yet. Add one below.
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-xs text-gray-500 text-left">
                <th className="px-4 py-3 font-medium">Account</th>
                <th className="px-4 py-3 font-medium text-center">Active</th>
                <th className="px-4 py-3 font-medium">Schedule</th>
                <th className="px-4 py-3 font-medium text-center">Status</th>
                <th className="px-4 py-3 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-medium text-white">{account.name}</span>
                    {account.group_number != null && (
                      <span className="ml-2 text-xs text-gray-500">Grp {account.group_number}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={account.enabled}
                      onChange={() => handleToggleEnabled(account)}
                      className="w-4 h-4 accent-blue-500 cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {scheduleLabel(settingsMap[account.id])}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        account.enabled
                          ? "bg-green-900 text-green-300"
                          : "bg-gray-800 text-gray-400"
                      }`}
                    >
                      {account.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-4">
                      <Link
                        href={`/dashboard/accounts/${account.id}`}
                        className="text-xs text-gray-400 hover:text-white transition-colors"
                      >
                        Settings
                      </Link>
                      <button
                        onClick={() => handleDelete(account.id, account.name)}
                        className="text-xs text-red-400 hover:text-red-300 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form onSubmit={handleAdd} className="flex gap-3">
        <input
          type="text"
          placeholder="Account name (Instagram handle)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="flex-1 bg-gray-800 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={adding}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          Add
        </button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  );
}
