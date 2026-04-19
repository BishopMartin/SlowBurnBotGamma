"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getAccounts,
  getAccountSettings,
  getAccountStats,
  createAccount,
  updateAccount,
  Account,
  AccountSettings,
  AccountStats,
} from "@/lib/api";
import { scheduleLabel } from "@/lib/format";
import { Bracket } from "@/lib/bracket";

function fmtGroup(n: number | null | undefined): React.ReactNode {
  if (n == null) return <span className="text-[#73726c]">—</span>;
  return <span className="text-[#73726c]">[{String(n).padStart(2, "0")}]</span>;
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "----";
  return v.toLocaleString();
}

function fmtPct(v: number | null): string {
  if (v == null) return "----";
  return `${Math.round(v * 100)}%`;
}

type Tab = "settings" | "stats";
type SortKey = "name" | "enabled" | "group" | "pending" | "complete" | "total" | "success" | "last_25" | "all_time";
type SortDir = "asc" | "desc";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [settingsMap, setSettingsMap] = useState<Record<string, AccountSettings>>({});
  const [statsMap, setStatsMap] = useState<Record<string, AccountStats>>({});
  const [tab, setTab] = useState<Tab>("settings");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sortedAccounts = useMemo(() => {
    const list = [...accounts];
    const dir = sortDir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      let av: number | string | null = null;
      let bv: number | string | null = null;
      switch (sortKey) {
        case "name": av = a.name.toLowerCase(); bv = b.name.toLowerCase(); break;
        case "enabled": av = a.enabled ? 1 : 0; bv = b.enabled ? 1 : 0; break;
        case "group": av = a.group_number ?? -1; bv = b.group_number ?? -1; break;
        case "pending": av = statsMap[a.id]?.pending ?? -1; bv = statsMap[b.id]?.pending ?? -1; break;
        case "complete": av = statsMap[a.id]?.complete ?? -1; bv = statsMap[b.id]?.complete ?? -1; break;
        case "total": av = statsMap[a.id]?.total ?? -1; bv = statsMap[b.id]?.total ?? -1; break;
        case "success": av = statsMap[a.id]?.success ?? -1; bv = statsMap[b.id]?.success ?? -1; break;
        case "last_25": av = statsMap[a.id]?.last_25 ?? -1; bv = statsMap[b.id]?.last_25 ?? -1; break;
        case "all_time": av = statsMap[a.id]?.all_time ?? -1; bv = statsMap[b.id]?.all_time ?? -1; break;
      }
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return list;
  }, [accounts, statsMap, sortKey, sortDir]);

  function SortTh({ label, field, className = "" }: { label: string; field: SortKey; className?: string }) {
    const active = sortKey === field;
    const arrow = active ? (sortDir === "asc" ? "↑" : "↓") : "\u00a0";
    return (
      <th
        className={`px-4 py-2 font-normal cursor-pointer select-none transition-colors hover:text-[#f0eee6] ${active ? "text-[#d97757]" : ""} ${className}`}
        onClick={() => toggleSort(field)}
      >
        <span className="whitespace-nowrap">{label}<span className="inline-block w-[1em] text-center">{arrow}</span></span>
      </th>
    );
  }

  async function load() {
    const data = await getAccounts().catch(() => []);
    setAccounts(data);
    const settingsEntries = await Promise.all(
      data.map((a) =>
        getAccountSettings(a.id)
          .then((s) => [a.id, s] as const)
          .catch(() => null)
      )
    );
    setSettingsMap(
      Object.fromEntries(settingsEntries.filter((e): e is [string, AccountSettings] => e !== null))
    );
    const statsEntries = await Promise.all(
      data.map((a) =>
        getAccountStats(a.id)
          .then((s) => [a.id, s] as const)
          .catch(() => null)
      )
    );
    setStatsMap(
      Object.fromEntries(statsEntries.filter((e): e is [string, AccountStats] => e !== null))
    );
  }

  useEffect(() => { load(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    setError("");
    try {
      await createAccount({ name: newName.trim(), enabled: false, group_number: 1 });
      setNewName("");
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create account.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggleEnabled(account: Account) {
    const updated = await updateAccount(account.id, { enabled: !account.enabled }).catch(() => null);
    if (updated) setAccounts((prev) => prev.map((a) => (a.id === account.id ? updated : a)));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h1 className="font-semibold text-[#f0eee6] font-mono">
          Accounts <span className="text-[#73726c] font-normal">[{String(accounts.length).padStart(2, "0")}/10]</span>
        </h1>
        <span className="text-[#73726c] font-mono">--</span>
        <div className="flex items-center gap-2 font-mono text-sm">
          <button
            onClick={() => setTab("settings")}
            className="group cursor-pointer transition-colors"
          >
            <Bracket className={tab === "settings" ? "text-[#d97757]" : "text-[#73726c] group-hover:text-[#f0eee6]"}>settings</Bracket>
          </button>
          <button
            onClick={() => setTab("stats")}
            className="group cursor-pointer transition-colors"
          >
            <Bracket className={tab === "stats" ? "text-[#d97757]" : "text-[#73726c] group-hover:text-[#f0eee6]"}>stats</Bracket>
          </button>
        </div>
      </div>

      <div className="border border-[#3d3d3a]">
        {accounts.length === 0 ? (
          <p className="px-4 py-6 font-mono text-[#73726c]">No accounts yet.</p>
        ) : (
          <table className="w-full font-mono">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <SortTh label="Account" field="name" />
                {tab === "settings" ? (
                  <>
                    <SortTh label="On" field="enabled" />
                    <SortTh label="Group" field="group" />
                    <th className="px-4 py-2 font-normal">Schedule</th>
                    <th className="px-4 py-2 font-normal">Status</th>
                  </>
                ) : (
                  <>
                    <SortTh label="Pend." field="pending" className="whitespace-nowrap" />
                    <SortTh label="Compl." field="complete" className="whitespace-nowrap" />
                    <SortTh label="Total" field="total" className="whitespace-nowrap" />
                    <SortTh label="Success" field="success" className="whitespace-nowrap" />
                    <SortTh label="Recent" field="last_25" className="whitespace-nowrap" />
                    <SortTh label="All" field="all_time" className="whitespace-nowrap" />
                  </>
                )}
                <th className="px-4 py-2 font-normal"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {sortedAccounts.map((account) => {
                const stats = statsMap[account.id];
                return (
                  <tr key={account.id} className="hover:bg-[#1f1e1d] transition-colors">
                    <td className="px-4 py-2 text-[#f0eee6]">{account.name}</td>
                    {tab === "settings" ? (
                      <>
                        <td className="px-4 py-2">
                          <button
                            onClick={() => handleToggleEnabled(account)}
                            className="group cursor-pointer transition-colors"
                          >
                            <Bracket className={account.enabled ? "text-[#73726c] group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                              {account.enabled ? "x" : "\u00a0"}
                            </Bracket>
                          </button>
                        </td>
                        <td className="px-4 py-2">{fmtGroup(account.group_number)}</td>
                        <td className="px-4 py-2 text-[#73726c]">
                          {scheduleLabel(settingsMap[account.id])}
                        </td>
                        <td className="px-4 py-2 font-mono">
                          <span className="text-[#73726c]">[</span>
                          <span className={account.enabled ? "text-green-400" : "text-red-400"}>{account.enabled ? "on" : "off"}</span>
                          <span className="text-[#73726c]">]</span>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-2 text-[#73726c]">{fmtNum(stats?.pending)}</td>
                        <td className="px-4 py-2 text-[#73726c]">{fmtNum(stats?.complete)}</td>
                        <td className="px-4 py-2 text-[#73726c]">{fmtNum(stats?.total)}</td>
                        <td className="px-4 py-2 text-[#73726c]">{fmtNum(stats?.success)}</td>
                        <td className="px-4 py-2 text-[#73726c]">{fmtPct(stats?.last_25 ?? null)}</td>
                        <td className="px-4 py-2 text-[#73726c]">{fmtPct(stats?.all_time ?? null)}</td>
                      </>
                    )}
                    <td className="px-4 py-2 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link href={`/dashboard/accounts/${account.id}`} className="group font-mono transition-colors">
                          <Bracket className="text-[#73726c] group-hover:text-[#d97757]">settings</Bracket>
                        </Link>
                        <Link href={`/dashboard/accounts/${account.id}/log`} className="group font-mono transition-colors">
                          <Bracket className="text-[#73726c] group-hover:text-[#d97757]">log</Bracket>
                        </Link>
                        <Link href={`/dashboard/accounts/${account.id}/database`} className="group font-mono transition-colors">
                          <Bracket className="text-[#73726c] group-hover:text-[#d97757]">data</Bracket>
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
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
              className="group font-mono disabled:opacity-50 transition-colors shrink-0"
            >
              <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">add</Bracket>
            </button>
          </form>
        </div>
      </div>

      {error && <p className="font-mono text-red-400">{error}</p>}
    </div>
  );
}
