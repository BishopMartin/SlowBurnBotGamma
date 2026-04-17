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
import { scheduleLabel } from "@/lib/format";

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
    <div className="space-y-4">
      <h1 className="font-semibold text-[#f0eee6]">Accounts</h1>

      <div className="border border-[#3d3d3a]">
        {accounts.length === 0 ? (
          <p className="px-4 py-6 font-mono text-[#73726c]">No accounts yet.</p>
        ) : (
          <table className="w-full font-mono">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <th className="px-4 py-2 font-normal">Account</th>
                <th className="px-4 py-2 font-normal">On</th>
                <th className="px-4 py-2 font-normal">Schedule</th>
                <th className="px-4 py-2 font-normal">Status</th>
                <th className="px-4 py-2 font-normal"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {accounts.map((account) => (
                <tr key={account.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-2 text-[#f0eee6]">
                    {account.name}
                    {account.group_number != null && (
                      <span className="ml-2 text-[#73726c]">grp:{account.group_number}</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => handleToggleEnabled(account)}
                      className="text-[#f0eee6] hover:text-[#d97757] transition-colors cursor-pointer"
                    >
                      {account.enabled ? "[x]" : "[ ]"}
                    </button>
                  </td>
                  <td className="px-4 py-2 text-[#73726c]">
                    {scheduleLabel(settingsMap[account.id])}
                  </td>
                  <td className="px-4 py-2">
                    <span className={account.enabled ? "text-green-400" : "text-[#73726c]"}>
                      {account.enabled ? "[on]" : "[off]"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex items-center justify-end gap-4">
                      <Link
                        href={`/dashboard/accounts/${account.id}`}
                        className="text-[#bfbdb4] hover:text-[#d97757] transition-colors"
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
        )}

        <div className="border-t border-[#3d3d3a]">
          <form onSubmit={handleAdd} className="flex items-center gap-2 px-4 py-3">
            <span className="font-mono text-[#73726c] shrink-0">Add:</span>
            <input
              type="text"
              placeholder="Instagram handle"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="flex-1 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-0.5 font-mono transition-colors"
            />
            <button
              type="submit"
              disabled={adding}
              className="font-mono text-[#d97757] hover:text-[#f0eee6] disabled:opacity-50 transition-colors shrink-0"
            >
              [Add]
            </button>
          </form>
        </div>
      </div>

      {error && <p className="font-mono text-red-400">{error}</p>}
    </div>
  );
}
