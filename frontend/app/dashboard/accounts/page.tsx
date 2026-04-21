"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getAccounts,
  getAccountSettings,
  getAccountStats,
  getLogSummary,
  getFollowbackSummary,
  createAccount,
  updateAccount,
  Account,
  AccountSettings,
  AccountStats,
  LogSummaryEntry,
  FollowbackSummaryEntry,
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

type Tab = "settings" | "activity" | "stats" | "database";
type SortKey = "name" | "enabled" | "group" | "pending" | "complete" | "total" | "success" | "last_25" | "all_time" | "sessions" | "likes" | "follows" | "unfollows" | "fb_rate" | "followed" | "followed_back";
type SortDir = "asc" | "desc";
type Period = "day" | "week" | "month";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [settingsMap, setSettingsMap] = useState<Record<string, AccountSettings>>({});
  const [statsMap, setStatsMap] = useState<Record<string, AccountStats>>({});
  const [logMap, setLogMap] = useState<Record<string, LogSummaryEntry>>({});
  const [fbMap, setFbMap] = useState<Record<string, FollowbackSummaryEntry>>({});
  const [tab, setTab] = useState<Tab>("settings");
  const [activityPeriod, setActivityPeriod] = useState<Period>("day");
  const [statsPeriod, setStatsPeriod] = useState<Period>("day");
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

  function getVal(account: Account, key: SortKey): number | string {
    switch (key) {
      case "name": return account.name.toLowerCase();
      case "enabled": return account.enabled ? 1 : 0;
      case "group": return account.group_number ?? -1;
      case "pending": return statsMap[account.id]?.pending ?? -1;
      case "complete": return statsMap[account.id]?.complete ?? -1;
      case "total": return statsMap[account.id]?.total ?? -1;
      case "success": return statsMap[account.id]?.success ?? -1;
      case "last_25": return statsMap[account.id]?.last_25 ?? -1;
      case "all_time": return statsMap[account.id]?.all_time ?? -1;
      case "sessions": return logMap[account.id]?.sessions ?? -1;
      case "likes": return logMap[account.id]?.likes ?? -1;
      case "follows": return logMap[account.id]?.follows ?? -1;
      case "unfollows": return logMap[account.id]?.unfollows ?? -1;
      case "fb_rate": return fbMap[account.id]?.rate ?? -1;
      case "followed": return fbMap[account.id]?.followed ?? -1;
      case "followed_back": return fbMap[account.id]?.followed_back ?? -1;
    }
  }

  const sortedAccounts = useMemo(() => {
    const list = [...accounts];
    const dir = sortDir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      const av = getVal(a, sortKey);
      const bv = getVal(b, sortKey);
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return list;
  }, [accounts, statsMap, logMap, fbMap, sortKey, sortDir]);

  function SortTh({ label, field, className = "" }: { label: string; field: SortKey; className?: string }) {
    const active = sortKey === field;
    const arrow = active ? (sortDir === "asc" ? "↑" : "↓") : "\u00a0";
    return (
      <th
        className={`px-2 py-2 font-normal cursor-pointer select-none transition-colors hover:text-[#f0eee6] ${active ? "text-[#d97757]" : ""} ${className}`}
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

  useEffect(() => {
    if (tab === "activity") {
      getLogSummary(activityPeriod).then(setLogMap).catch(() => {});
    }
  }, [tab, activityPeriod]);

  useEffect(() => {
    if (tab === "stats") {
      getFollowbackSummary(statsPeriod).then(setFbMap).catch(() => {});
    }
  }, [tab, statsPeriod]);

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

  function PeriodSelect({ value, onChange, options }: { value: Period; onChange: (p: Period) => void; options?: { value: Period; label: string }[] }) {
    const opts = options ?? [
      { value: "day", label: "day" },
      { value: "week", label: "week" },
      { value: "month", label: "month" },
    ];
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Period)}
        className="bg-transparent text-[#73726c] border border-[#3d3d3a] text-xs px-1 py-0.5 cursor-pointer outline-none focus:border-[#d97757] transition-colors"
      >
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "settings", label: "settings" },
    { key: "activity", label: "activity" },
    { key: "stats", label: "stats" },
    { key: "database", label: "database" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <h1 className="font-semibold text-[#f0eee6] font-mono">
          Accounts <span className="text-[#73726c] font-normal">[{String(accounts.length).padStart(2, "0")}/10]</span>
        </h1>
        <span className="text-[#73726c] font-mono">--</span>
        <div className="flex items-center gap-2 font-mono text-sm">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={tab === t.key ? "text-[#d97757]" : "text-[#73726c] group-hover:text-[#f0eee6]"}>{t.label}</Bracket>
            </button>
          ))}
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
                {tab === "settings" && (
                  <>
                    <SortTh label="On" field="enabled" />
                    <SortTh label="Group" field="group" />
                    <th className="px-2 py-2 font-normal">Schedule</th>
                    <th className="px-2 py-2 font-normal">Runs/Day</th>
                    <th className="px-2 py-2 font-normal">Status</th>
                  </>
                )}
                {tab === "activity" && (
                  <>
                    <SortTh label="Sessions" field="sessions" className="whitespace-nowrap" />
                    <SortTh label="Likes" field="likes" className="whitespace-nowrap" />
                    <SortTh label="Follows" field="follows" className="whitespace-nowrap" />
                    <SortTh label="Unfollows" field="unfollows" className="whitespace-nowrap" />
                  </>
                )}
                {tab === "stats" && (
                  <>
                    <SortTh label="Followed" field="followed" className="whitespace-nowrap" />
                    <SortTh label="Followed Back" field="followed_back" className="whitespace-nowrap" />
                    <SortTh label="FB Rate" field="fb_rate" className="whitespace-nowrap" />
                    <th className="px-2 py-2 font-normal text-right">
                      <PeriodSelect value={statsPeriod} onChange={setStatsPeriod} />
                    </th>
                  </>
                )}
                {tab === "database" && (
                  <>
                    <SortTh label="Pend." field="pending" className="whitespace-nowrap" />
                    <SortTh label="Compl." field="complete" className="whitespace-nowrap" />
                    <SortTh label="Total" field="total" className="whitespace-nowrap" />
                    <SortTh label="Success" field="success" className="whitespace-nowrap" />
                    <SortTh label="Recent" field="last_25" className="whitespace-nowrap" />
                    <SortTh label="All" field="all_time" className="whitespace-nowrap" />
                  </>
                )}
                <th className="px-2 py-2 font-normal w-full text-right whitespace-nowrap">
                  {tab === "activity" && (
                    <span className="inline-flex items-center gap-1">
                      <span className="text-[#73726c]">activity:</span>
                      <PeriodSelect
                        value={activityPeriod}
                        onChange={setActivityPeriod}
                        options={[
                          { value: "day", label: "today" },
                          { value: "week", label: "last 7 days" },
                          { value: "month", label: "last 30 days" },
                        ]}
                      />
                    </span>
                  )}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {sortedAccounts.map((account) => {
                const stats = statsMap[account.id];
                const log = logMap[account.id];
                const fb = fbMap[account.id];
                return (
                  <tr key={account.id} className="hover:bg-[#1f1e1d] transition-colors">
                    <td className="px-2 pr-6 py-2 text-[#f0eee6] whitespace-nowrap overflow-hidden text-ellipsis" style={{ maxWidth: "20ch" }}>{account.name}</td>
                    {tab === "settings" && (
                      <>
                        <td className="px-2 py-2 whitespace-nowrap">
                          <button
                            onClick={() => handleToggleEnabled(account)}
                            className="group cursor-pointer transition-colors"
                          >
                            <Bracket className={account.enabled ? "text-[#73726c] group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                              {account.enabled ? "x" : "\u00a0"}
                            </Bracket>
                          </button>
                        </td>
                        <td className="px-2 py-2 whitespace-nowrap">{fmtGroup(account.group_number)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">
                          {scheduleLabel(settingsMap[account.id])}
                        </td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">
                          {settingsMap[account.id]?.max_runs_per_day ?? "—"}
                        </td>
                        <td className="px-2 py-2 font-mono whitespace-nowrap">
                          <span className="text-[#73726c]">[</span>
                          <span className={account.enabled ? "text-green-400" : "text-red-400"}>{account.enabled ? "on" : "off"}</span>
                          <span className="text-[#73726c]">]</span>
                        </td>
                      </>
                    )}
                    {tab === "activity" && (
                      <>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(log?.sessions)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(log?.likes)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(log?.follows)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(log?.unfollows)}</td>
                      </>
                    )}
                    {tab === "stats" && (
                      <>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(fb?.followed)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(fb?.followed_back)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtPct(fb?.rate ?? null)}</td>
                        <td></td>
                      </>
                    )}
                    {tab === "database" && (
                      <>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(stats?.pending)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(stats?.complete)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(stats?.total)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtNum(stats?.success)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtPct(stats?.last_25 ?? null)}</td>
                        <td className="px-2 py-2 text-[#73726c] whitespace-nowrap">{fmtPct(stats?.all_time ?? null)}</td>
                      </>
                    )}
                    <td className="px-2 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {tab === "settings" && (
                          <Link href={`/dashboard/accounts/${account.id}`} className="group font-mono transition-colors">
                            <Bracket className="text-[#73726c] group-hover:text-[#d97757]">settings</Bracket>
                          </Link>
                        )}
                        {tab === "activity" && (
                          <Link href={`/dashboard/accounts/${account.id}/log`} className="group font-mono transition-colors">
                            <Bracket className="text-[#73726c] group-hover:text-[#d97757]">log</Bracket>
                          </Link>
                        )}
                        {tab === "stats" && (
                          <Link href={`/dashboard/accounts/${account.id}/database`} className="group font-mono transition-colors">
                            <Bracket className="text-[#73726c] group-hover:text-[#d97757]">stats</Bracket>
                          </Link>
                        )}
                        {tab === "database" && (
                          <Link href={`/dashboard/accounts/${account.id}/database`} className="group font-mono transition-colors">
                            <Bracket className="text-[#73726c] group-hover:text-[#d97757]">data</Bracket>
                          </Link>
                        )}
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
            <span className="font-mono text-[#73726c] shrink-0">Insert New Account:</span>
            <input
              type="text"
              placeholder="Account Name"
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
