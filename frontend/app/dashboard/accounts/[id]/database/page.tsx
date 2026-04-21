"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getAccounts, getAccountDatabase, Account, FollowTarget } from "@/lib/api";

const PAGE_SIZE = 100;

type SortKey = "handle" | "source" | "status" | "followed" | "unfollowed" | "fb";
type SortDir = "asc" | "desc";

function statusCls(status: string): string {
  if (status === "done") return "text-[#CCCC00]";
  if (status === "skipped") return "text-[#73726c]";
  return "text-[#f0eee6]";
}

export default function AccountDatabasePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [items, setItems] = useState<FollowTarget[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("followed");
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
    getAccountDatabase(id, page, PAGE_SIZE, sortKey, sortDir)
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
        <span className="text-[#73726c]">/ database</span>
        <span className="text-[#73726c] ml-auto">[{total.toLocaleString()} records]</span>
      </div>

      <div className="border border-[#3d3d3a]">
        {loading ? (
          <p className="px-4 py-6 text-[#73726c]">loading…</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-[#73726c]">no records found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <SortTh label="handle" field="handle" />
                <SortTh label="source" field="source" />
                <SortTh label="status" field="status" />
                <SortTh label="followed" field="followed" />
                <SortTh label="unfollowed" field="unfollowed" />
                <SortTh label="fb" field="fb" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {items.map((t) => (
                <tr key={t.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-1.5 text-[#f0eee6]">{t.target_handle}</td>
                  <td className="px-4 py-1.5 text-[#73726c] text-xs">{t.source ?? "—"}</td>
                  <td className={`px-4 py-1.5 ${statusCls(t.status)}`}>{t.status}</td>
                  <td className="px-4 py-1.5 text-[#73726c]">{t.follow_date ?? "—"}</td>
                  <td className="px-4 py-1.5 text-[#73726c]">{t.unfollow_date ?? "—"}</td>
                  <td className={`px-4 py-1.5 ${t.follow_back === true ? "text-[#CCCC00]" : t.follow_back === false ? "text-[#FF6600]" : "text-[#73726c]"}`}>
                    {t.follow_back === true ? "yes" : t.follow_back === false ? "no" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-4 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="disabled:opacity-30 text-[#73726c] hover:text-[#f0eee6] transition-colors"
          >
            [prev]
          </button>
          <span className="text-[#73726c]">
            page {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="disabled:opacity-30 text-[#73726c] hover:text-[#f0eee6] transition-colors"
          >
            [next]
          </button>
        </div>
      )}
    </div>
  );
}
