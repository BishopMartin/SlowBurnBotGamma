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

const inputCls =
  "bg-[#262624] rounded-lg px-3 py-2 text-[#f0eee6] placeholder-[#73726c] outline-none border border-[#3d3d3a] focus:border-[#d97757] focus:ring-1 focus:ring-[#d97757] transition-colors";

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
      <h1 className="font-semibold text-[#f0eee6]">Accounts</h1>

      {accounts.length === 0 ? (
        <div className="bg-[#1f1e1d] rounded-xl p-8 text-center text-[#73726c] border border-[#3d3d3a]">
          No accounts yet. Add one below.
        </div>
      ) : (
        <div className="bg-[#1f1e1d] rounded-xl overflow-hidden border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#3d3d3a] text-left text-[#73726c]">
                <th className="px-4 py-3 font-medium">Account</th>
                <th className="px-4 py-3 font-medium text-center">Active</th>
                <th className="px-4 py-3 font-medium">Schedule</th>
                <th className="px-4 py-3 font-medium text-center">Status</th>
                <th className="px-4 py-3 font-medium text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-[#262624] transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-medium text-[#f0eee6]">{account.name}</span>
                    {account.group_number != null && (
                      <span className="ml-2 text-[#73726c]">Grp {account.group_number}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={account.enabled}
                      onChange={() => handleToggleEnabled(account)}
                      className="w-4 h-4 accent-[#d97757] cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 text-[#73726c]">
                    {scheduleLabel(settingsMap[account.id])}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded-full ${
                        account.enabled
                          ? "bg-[#1a2e1a] text-green-400"
                          : "bg-[#262624] text-[#73726c]"
                      }`}
                    >
                      {account.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-4">
                      <Link
                        href={`/dashboard/accounts/${account.id}`}
                        className="text-[#bfbdb4] hover:text-[#f0eee6] transition-colors"
                      >
                        Settings
                      </Link>
                      <button
                        onClick={() => handleDelete(account.id, account.name)}
                        className="text-red-400 hover:text-red-300 transition-colors"
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
          className={`flex-1 ${inputCls}`}
        />
        <button
          type="submit"
          disabled={adding}
          className="bg-[#c6613f] hover:bg-[#d97757] disabled:opacity-50 rounded-lg px-4 py-2 font-medium text-[#f0eee6] transition-colors"
        >
          Add
        </button>
      </form>
      {error && <p className="text-red-400">{error}</p>}
    </div>
  );
}
