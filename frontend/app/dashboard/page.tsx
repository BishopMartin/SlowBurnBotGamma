"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getAccounts, getEntitlement, Account, Entitlement } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

export default function DashboardPage() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [entitlement, setEntitlement] = useState<Entitlement | null>(null);

  useEffect(() => {
    getAccounts().then(setAccounts).catch(() => {});
    getEntitlement().then(setEntitlement).catch(() => {});
  }, []);

  const enabledCount = accounts.filter((a) => a.enabled).length;

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f0eee6]">
        welcome back{user?.display_name ? `, ${user.display_name}` : ""}
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          {
            label: "plan",
            value: entitlement?.plan_tier ?? user?.plan_tier ?? "free",
            sub: entitlement?.active ? (
              <span className="text-green-400">active</span>
            ) : (
              <span className="text-yellow-400">inactive</span>
            ),
          },
          { label: "total accounts", value: String(accounts.length), sub: null },
          { label: "enabled accounts", value: String(enabledCount), sub: null },
        ].map(({ label, value, sub }) => (
          <div key={label} className="border border-[#3d3d3a] px-4 py-3">
            <div className="text-[#73726c]">{label}</div>
            <div className="text-[#f0eee6] font-semibold mt-1 capitalize">{value}</div>
            {sub && <div className="mt-0.5">{sub}</div>}
          </div>
        ))}
      </div>

      <div className="border border-[#3d3d3a]">
        <div className="flex items-center justify-between border-b border-[#3d3d3a] px-4 py-2">
          <span className="text-[#f0eee6]">accounts</span>
          <Link href="/dashboard/accounts" className="text-[#d97757] hover:text-[#f0eee6] transition-colors">
            manage →
          </Link>
        </div>
        {accounts.length === 0 ? (
          <div className="px-4 py-6 text-[#73726c]">
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
                  <td className="px-4 py-2 text-[#f0eee6]">
                    {account.name}
                    {account.group_number != null && (
                      <span className="ml-2 text-[#73726c]">grp:{account.group_number}</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Bracket className={account.enabled ? "text-green-400" : "text-[#73726c]"}>
                      {account.enabled ? "on" : "off"}
                    </Bracket>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
