"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { getAccounts, getEntitlement, Account, Entitlement } from "@/lib/api";

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
    <div className="space-y-6">
      <h1 className="font-semibold text-[#f0eee6]">
        Welcome back{user?.display_name ? `, ${user.display_name}` : ""}
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#1f1e1d] rounded-xl p-4 border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <p className="text-[#73726c] mb-1">Plan</p>
          <p className="font-semibold text-[#f0eee6] capitalize">
            {entitlement?.plan_tier ?? user?.plan_tier ?? "free"}
          </p>
          <p className={`mt-1 ${entitlement?.active ? "text-green-400" : "text-yellow-400"}`}>
            {entitlement?.active ? "Active" : "Inactive"}
          </p>
        </div>
        <div className="bg-[#1f1e1d] rounded-xl p-4 border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <p className="text-[#73726c] mb-1">Total accounts</p>
          <p className="font-semibold text-[#f0eee6]">{accounts.length}</p>
        </div>
        <div className="bg-[#1f1e1d] rounded-xl p-4 border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          <p className="text-[#73726c] mb-1">Enabled accounts</p>
          <p className="font-semibold text-[#f0eee6]">{enabledCount}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="font-medium text-[#f0eee6]">Accounts</h2>
        <Link href="/dashboard/accounts" className="text-[#d97757] hover:underline">
          Manage →
        </Link>
      </div>

      {accounts.length === 0 ? (
        <div className="bg-[#1f1e1d] rounded-xl p-8 text-center text-[#73726c] border border-[#3d3d3a]">
          No accounts yet.{" "}
          <Link href="/dashboard/accounts" className="text-[#d97757] hover:underline">
            Add one
          </Link>
        </div>
      ) : (
        <div className="bg-[#1f1e1d] rounded-xl divide-y divide-[#3d3d3a] border border-[#3d3d3a]" style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.08)" }}>
          {accounts.slice(0, 5).map((account) => (
            <div key={account.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-[#f0eee6]">{account.name}</p>
                {account.group_number != null && (
                  <p className="text-[#73726c]">Group {account.group_number}</p>
                )}
              </div>
              <span
                className={`px-2 py-0.5 rounded-full ${
                  account.enabled
                    ? "bg-[#1a2e1a] text-green-400"
                    : "bg-[#262624] text-[#73726c]"
                }`}
              >
                {account.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
