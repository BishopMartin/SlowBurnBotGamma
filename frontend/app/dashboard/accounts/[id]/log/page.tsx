"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getAccounts, getAccountLog, Account, SessionLogEntry } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

const PAGE_SIZE = 100;

type SortKey = "date" | "run" | "start" | "end" | "a1_type" | "a1_count" | "a2_type" | "a2_count" | "a3_type" | "a3_count" | "a4_type" | "a4_count" | "error";
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

function fmtAction(type: string | null, count: number): string {
  if (!type) return "—";
  return `${type} (${count})`;
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
        className={`px-4 py-2 font-normal cursor-pointer select-none transition-colors hover:text-[#f0eee6] ${active ? "text-[#d97757]" : ""} ${className}`}
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
        <Link href="/dashboard/accounts" className="text-[#73726c] hover:text-[#f0eee6] transition-colors">
          ← accounts
        </Link>
        <span className="text-[#3d3d3a]">/</span>
        <span className="text-[#f0eee6]">{account.name}</span>
        <span className="text-[#73726c]">/ log</span>
        <span className="text-[#73726c] ml-auto">[{total.toLocaleString()} entries]</span>
      </div>

      <div className="border border-[#3d3d3a]">
        {loading ? (
          <p className="px-4 py-6 text-[#73726c]">loading...</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-[#73726c]">no log entries found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                  <SortTh label="date" field="date" />
                  <SortTh label="run" field="run" />
                  <SortTh label="start" field="start" />
                  <SortTh label="end" field="end" />
                  <SortTh label="action 1" field="a1_type" />
                  <SortTh label="action 2" field="a2_type" />
                  <SortTh label="action 3" field="a3_type" />
                  <SortTh label="action 4" field="a4_type" />
                  <SortTh label="error" field="error" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3d3d3a]">
                {items.map((entry) => (
                  <tr key={entry.id} className="hover:bg-[#1f1e1d] transition-colors">
                    <td className="px-4 py-1.5 text-[#f0eee6]">{entry.run_date ?? "—"}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{entry.run_sequence}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtTime(entry.start_time)}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtTime(entry.end_time)}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtAction(entry.action_1_type, entry.action_1_count)}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtAction(entry.action_2_type, entry.action_2_count)}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtAction(entry.action_3_type, entry.action_3_count)}</td>
                    <td className="px-4 py-1.5 text-[#73726c]">{fmtAction(entry.action_4_type, entry.action_4_count)}</td>
                    <td className={`px-4 py-1.5 ${entry.error_message ? "text-red-400" : "text-[#73726c]"}`}>
                      {entry.error_message ?? "—"}
                    </td>
                  </tr>
                ))}
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
            <Bracket className="text-[#73726c] hover:text-[#f0eee6]">prev</Bracket>
          </button>
          <span className="text-[#73726c]">
            page {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="disabled:opacity-30 transition-colors"
          >
            <Bracket className="text-[#73726c] hover:text-[#f0eee6]">next</Bracket>
          </button>
        </div>
      )}
    </div>
  );
}
