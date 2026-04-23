"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { adminListAccounts, adminGetFollowTargets, AdminAccount, FollowTarget } from "@/lib/api";

const PAGE_SIZE = 100;

function statusCls(status: string): string {
  if (status === "done") return "text-status-ok";
  if (status === "skipped") return "text-[#9A968B]";
  return "text-[#f4f3ee]";
}

export default function FollowTargetsPage() {
  const { id } = useParams<{ id: string }>();
  const [account, setAccount] = useState<AdminAccount | null>(null);
  const [items, setItems] = useState<FollowTarget[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminListAccounts()
      .then((all) => setAccount(all.find((a) => a.id === id) ?? null))
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    setLoading(true);
    adminGetFollowTargets(id, page, PAGE_SIZE)
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id, page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4 font-mono">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/admin/accounts" className="text-[#9A968B] hover:text-[#f4f3ee] transition-colors">
          ← accounts
        </Link>
        <span className="text-[#3d3d3a]">/</span>
        <span className="text-[#f4f3ee]">{account?.name ?? id}</span>
        <span className="text-[#9A968B]">follow-targets</span>
        <span className="text-[#9A968B] ml-auto">
          [{total.toLocaleString()} total]
        </span>
      </div>

      <div className="border border-[#3d3d3a]">
        {loading ? (
          <p className="px-4 py-6 text-[#9A968B]">loading…</p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-[#9A968B]">no records found.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a] bg-[#1a1918]">
                <th className="px-4 py-2 font-normal">handle</th>
                <th className="px-4 py-2 font-normal">source</th>
                <th className="px-4 py-2 font-normal">status</th>
                <th className="px-4 py-2 font-normal">followed</th>
                <th className="px-4 py-2 font-normal">unfollowed</th>
                <th className="px-4 py-2 font-normal">fb</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {items.map((t) => (
                <tr key={t.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-1.5 text-[#f4f3ee]">{t.target_handle}</td>
                  <td className="px-4 py-1.5 text-[#9A968B] text-xs">{t.source ?? "—"}</td>
                  <td className={`px-4 py-1.5 ${statusCls(t.status)}`}>{t.status}</td>
                  <td className="px-4 py-1.5 text-[#9A968B]">{t.follow_date ?? "—"}</td>
                  <td className="px-4 py-1.5 text-[#9A968B]">{t.unfollow_date ?? "—"}</td>
                  <td className="px-4 py-1.5 text-[#9A968B]">
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
            className="disabled:opacity-30 text-[#9A968B] hover:text-[#f4f3ee] transition-colors"
          >
            [prev]
          </button>
          <span className="text-[#9A968B]">
            page {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="disabled:opacity-30 text-[#9A968B] hover:text-[#f4f3ee] transition-colors"
          >
            [next]
          </button>
        </div>
      )}
    </div>
  );
}
