"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAccounts, createAccount, deleteAccount, Account } from "@/lib/api";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    const data = await getAccounts().catch(() => []);
    setAccounts(data);
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

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Accounts</h1>

      <form onSubmit={handleAdd} className="flex gap-3">
        <input
          type="text"
          placeholder="Account name (Instagram handle)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="flex-1 bg-gray-800 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
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

      {accounts.length === 0 ? (
        <div className="bg-gray-900 rounded-xl p-8 text-center text-gray-400 text-sm">
          No accounts yet. Add one above.
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl divide-y divide-gray-800">
          {accounts.map((account) => (
            <div key={account.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <Link
                  href={`/dashboard/accounts/${account.id}`}
                  className="text-sm font-medium hover:text-blue-400 transition-colors"
                >
                  {account.name}
                </Link>
                {account.group_number != null && (
                  <p className="text-xs text-gray-400">Group {account.group_number}</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    account.enabled
                      ? "bg-green-900 text-green-300"
                      : "bg-gray-800 text-gray-400"
                  }`}
                >
                  {account.enabled ? "Enabled" : "Disabled"}
                </span>
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
