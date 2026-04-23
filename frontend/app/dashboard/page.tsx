"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  getAccounts,
  getEntitlement,
  getRecentSessionLog,
  Account,
  Entitlement,
  RecentSessionLogEntry,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { formatSessionAction } from "@/lib/format";

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const h = d.getHours();
  const m = d.getMinutes();
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")}${period}`;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [entitlement, setEntitlement] = useState<Entitlement | null>(null);
  const [recentLog, setRecentLog] = useState<RecentSessionLogEntry[]>([]);

  useEffect(() => {
    getAccounts().then(setAccounts).catch(() => {});
    getEntitlement().then(setEntitlement).catch(() => {});
    getRecentSessionLog(15).then((r) => setRecentLog(r.items)).catch(() => {});
  }, []);

  const enabledCount = accounts.filter((a) => a.enabled).length;

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">
        Overview{user?.display_name ? ` — ${user.display_name}` : ""}
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          {
            label: "plan",
            value: entitlement?.plan_tier ?? user?.plan_tier ?? "free",
            sub: entitlement?.active ? (
              <span className="text-status-ok">active</span>
            ) : (
              <span className="text-status-bad">inactive</span>
            ),
          },
          { label: "total accounts", value: String(accounts.length), sub: null },
          { label: "enabled accounts", value: String(enabledCount), sub: null },
        ].map(({ label, value, sub }) => (
          <div
            key={label}
            className="border border-[#3d3d3a] px-4 py-2.5 flex flex-row items-center justify-between gap-3 min-w-0"
          >
            <span className="text-[#9A968B] shrink-0">{label}</span>
            <div className="flex items-center gap-2 min-w-0 justify-end">
              <span className="text-[#f4f3ee] font-semibold capitalize truncate">{value}</span>
              {sub}
            </div>
          </div>
        ))}
      </div>

      <div className="border border-[#3d3d3a]">
        <div className="flex items-center justify-between border-b border-[#3d3d3a] px-4 py-2 bg-[#1a1918]">
          <span className="text-[#f4f3ee]">accounts</span>
          <Link href="/dashboard/accounts" className="text-[#d97757] hover:text-[#f4f3ee] transition-colors">
            manage →
          </Link>
        </div>
        {accounts.length === 0 ? (
          <div className="px-4 py-6 text-[#9A968B]">
            no accounts yet.{" "}
            <Link href="/dashboard/accounts" className="text-[#d97757] hover:underline">
              add one
            </Link>
          </div>
        ) : (
          <table className="w-full">
            <tbody className="divide-y divide-[#3d3d3a]">
              {accounts.slice(0, 5).map((account) => (
                <tr key={account.id}>
                  <td className="px-4 py-2 text-[#f4f3ee]">
                    {account.name}
                    {account.group_number != null && (
                      <span className="ml-2 text-[#9A968B]">grp:{account.group_number}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Bracket className={account.enabled ? "text-status-ok" : "text-[#9A968B]"}>
                      {account.enabled ? "on" : "off"}
                    </Bracket>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="border border-[#3d3d3a]">
        <div className="flex items-center justify-between border-b border-[#3d3d3a] px-4 py-2 bg-[#1a1918]">
          <span className="text-[#f4f3ee]">recent activity</span>
          <Link href="/dashboard/accounts" className="text-[#d97757] hover:text-[#f4f3ee] transition-colors">
            by account →
          </Link>
        </div>
        {recentLog.length === 0 ? (
          <div className="px-4 py-6 text-[#9A968B]">no session log entries yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a]">
                  <th className="px-2 py-2 font-normal whitespace-nowrap">account</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">date</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">run</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">start</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">end</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">action 1</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">action 2</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">action 3</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">action 4</th>
                  <th className="px-2 py-2 font-normal whitespace-nowrap">errors</th>
                </tr>
              </thead>
              <tbody>
                {recentLog.map((entry, idx) => {
                  const prevDate = idx > 0 ? recentLog[idx - 1].run_date : null;
                  const isNewDay = idx > 0 && entry.run_date !== prevDate;
                  return (
                  <tr key={entry.id} className={`hover:bg-[#1f1e1d] transition-colors ${isNewDay ? "border-t-2 border-[#3d3d3a]" : "border-t border-[#3d3d3a]"}`}>
                    <td className="px-2 py-1.5 whitespace-nowrap">
                      <Link
                        href={`/dashboard/accounts/${entry.account_id}/log`}
                        className="text-[#d97757] hover:text-[#f4f3ee] transition-colors"
                      >
                        {entry.account_name}
                      </Link>
                    </td>
                    <td className="px-2 py-1.5 text-[#f4f3ee] whitespace-nowrap">{entry.run_date ?? "—"}</td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">{entry.run_sequence}</td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">{fmtTime(entry.start_time)}</td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">{fmtTime(entry.end_time)}</td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">
                      {formatSessionAction(entry.action_1_type, entry.action_1_count)}
                    </td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">
                      {formatSessionAction(entry.action_2_type, entry.action_2_count)}
                    </td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">
                      {formatSessionAction(entry.action_3_type, entry.action_3_count)}
                    </td>
                    <td className="px-2 py-1.5 text-[#9A968B] whitespace-nowrap">
                      {formatSessionAction(entry.action_4_type, entry.action_4_count)}
                    </td>
                    <td className="px-2 py-1.5 whitespace-nowrap">
                      {entry.error_message ? (
                        <span className="text-status-bad text-xs" title={entry.error_message}>
                          error
                        </span>
                      ) : (
                        <span className="text-[#3d3d3a] text-xs">none</span>
                      )}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
