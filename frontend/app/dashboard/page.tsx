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
      <h1 className="text-xl font-semibold">
        Welcome back{user?.display_name ? `, ${user.display_name}` : ""}
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-gray-900 rounded-xl p-4">
          <p className="text-sm text-gray-400 mb-1">Plan</p>
          <p className="text-lg font-semibold capitalize">
            {entitlement?.plan_tier ?? user?.plan_tier ?? "free"}
          </p>
          <p className={`text-xs mt-1 ${entitlement?.active ? "text-green-400" : "text-yellow-400"}`}>
            {entitlement?.active ? "Active" : "Inactive"}
          </p>
        </div>
        <div className="bg-gray-900 rounded-xl p-4">
          <p className="text-sm text-gray-400 mb-1">Total accounts</p>
          <p className="text-lg font-semibold">{accounts.length}</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-4">
          <p className="text-sm text-gray-400 mb-1">Enabled accounts</p>
          <p className="text-lg font-semibold">{enabledCount}</p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="font-medium">Accounts</h2>
        <Link href="/dashboard/accounts" className="text-sm text-blue-400 hover:underline">
          Manage →
        </Link>
      </div>

      {accounts.length === 0 ? (
        <div className="bg-gray-900 rounded-xl p-8 text-center text-gray-400 text-sm">
          No accounts yet.{" "}
          <Link href="/dashboard/accounts" className="text-blue-400 hover:underline">
            Add one
          </Link>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl divide-y divide-gray-800">
          {accounts.slice(0, 5).map((account) => (
            <div key={account.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{account.name}</p>
                {account.group_number != null && (
                  <p className="text-xs text-gray-400">Group {account.group_number}</p>
                )}
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  account.enabled
                    ? "bg-green-900 text-green-300"
                    : "bg-gray-800 text-gray-400"
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
