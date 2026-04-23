"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getAccounts, getAccountLog, Account, SessionLogEntry } from "@/lib/api";
import { formatSessionAction } from "@/lib/format";
import { Bracket } from "@/lib/bracket";

const PAGE_SIZE = 100;

type SortKey = "date" | "run" | "start" | "end" | "a1_type" | "a1_count" | "a2_type" | "a2_count" | "a3_type" | "a3_count" | "a4_type" | "a4_count" | "error";
const COL_COUNT = 10;
type SortDir = "asc" | "desc";

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const h = d.getHours();
  const m = d.getMinutes();
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")}${period}`;
}

export default function AccountLogPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [items, setItems] = useState<SessionLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());

  const toggleError = useCallback((id: string) => {
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  }

  function SortTh({ label, field, className = "" }: { label: string; field: SortKey; className?: string }) {
    const active = sortKey === field;
    const arrow = active ? (sortDir === "asc" ? "↑" : "↓") : "\u00a0";
    return (
      <th
        className={`px-2 py-2 font-normal cursor-pointer select-none transition-colors hover:text-[#f4f3ee] ${active ? "text-[#d97757]" : ""} ${className}`}
        onClick={() => toggleSort(field)}
      >
        <span className="whitespace-nowrap">{label}<span className="inline-block w-[1em] text-center">{arrow}</span></span>
      </th>
    );
  }

  useEffect(() => {
    getAccounts()
      .then((all) => {
        const found = all.find((a) => a.id === id);
        if (!found) router.push("/dashboard/accounts");
        else setAccount(found);
      })
      .catch(() => router.push("/dashboard/accounts"));
  }, [id, router]);

  useEffect(() => {
    setLoading(true);
    getAccountLog(id, page, PAGE_SIZE, sortKey, sortDir)
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id, page, sortKey, sortDir]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  if (!account) return null;

  return (
    <div className="space-y-4 font-mono">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/dashboard/accounts" className="text-[#B1ADA1] hover:text-[#f4f3ee] transition-colors">
          ← accounts
        </Link>
        <span className="text-[#3d3d3a]">/</span>
        <span className="text-[#f4f3ee]">{account.name}</span>
        <span className="text-[#B1ADA1]">/ log</span>
        <span className="text-[#B1ADA1] ml-auto">[{total.toLocaleString()} entries]</span>
      </div>

      <div className="border border-[#3d3d3a]">
        {loading ? (
          <p className="px-4 py-6 text-[#B1ADA1]">loading...</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-[#B1ADA1]">no log entries found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#B1ADA1] border-b border-[#3d3d3a]">
                  <SortTh label="date" field="date" />
                  <SortTh label="run" field="run" />
                  <SortTh label="start" field="start" />
                  <SortTh label="end" field="end" />
                  <SortTh label="action 1" field="a1_type" />
                  <SortTh label="action 2" field="a2_type" />
                  <SortTh label="action 3" field="a3_type" />
                  <SortTh label="action 4" field="a4_type" />
                  <th className="px-2 py-2 font-normal">errors</th>
                  <th className="w-full"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((entry, idx) => {
                  const prevDate = idx > 0 ? items[idx - 1].run_date : null;
                  const isNewDay = idx > 0 && entry.run_date !== prevDate;
                  return (
                  <>
                    <tr key={entry.id} className={`hover:bg-[#1f1e1d] transition-colors ${isNewDay ? "border-t-2 border-[#B1ADA1]" : "border-t border-[#3d3d3a]"}`}>
                      <td className="px-2 py-1.5 text-[#f4f3ee] whitespace-nowrap">{entry.run_date ?? "—"}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{entry.run_sequence}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{fmtTime(entry.start_time)}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{fmtTime(entry.end_time)}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{formatSessionAction(entry.action_1_type, entry.action_1_count)}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{formatSessionAction(entry.action_2_type, entry.action_2_count)}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{formatSessionAction(entry.action_3_type, entry.action_3_count)}</td>
                      <td className="px-2 py-1.5 text-[#B1ADA1] whitespace-nowrap">{formatSessionAction(entry.action_4_type, entry.action_4_count)}</td>
                      <td className="px-2 py-1.5 whitespace-nowrap">
                        {entry.error_message ? (
                          <button
                            onClick={() => toggleError(entry.id)}
                            className="text-status-bad hover:text-status-bad-hover cursor-pointer transition-colors text-xs"
                          >
                            {expandedErrors.has(entry.id) ? "▾ error" : "▸ error"}
                          </button>
                        ) : (
                          <span className="text-[#3d3d3a] text-xs">none</span>
                        )}
                      </td>
                      <td></td>
                    </tr>
                    {entry.error_message && expandedErrors.has(entry.id) && (
                      <tr key={`${entry.id}-err`} className="bg-[#1f1e1d]">
                        <td colSpan={COL_COUNT} className="px-2 py-1 text-status-bad text-xs whitespace-pre-wrap">
                          {entry.error_message.split("\n").map((line) => `- ${line}`).join("\n")}
                        </td>
                      </tr>
                    )}
                  </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-4 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="disabled:opacity-30 transition-colors"
          >
            <Bracket className="text-[#B1ADA1] hover:text-[#f4f3ee]">prev</Bracket>
          </button>
          <span className="text-[#B1ADA1]">
            page {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="disabled:opacity-30 transition-colors"
          >
            <Bracket className="text-[#B1ADA1] hover:text-[#f4f3ee]">next</Bracket>
          </button>
        </div>
      )}
    </div>
  );
}
