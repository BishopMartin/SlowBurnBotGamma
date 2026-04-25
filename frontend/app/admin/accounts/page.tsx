"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminListAccounts, adminDeleteAccount, AdminAccount } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    adminListAccounts().then(setAccounts).catch(() => {});
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(account: AdminAccount) {
    if (!confirm(`Delete account "${account.name}" (${account.user_email})? This cannot be undone.`)) return;
    setBusy(account.id);
    setError(null);
    try {
      await adminDeleteAccount(account.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "delete failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">
        admin — accounts{" "}
        <span className="text-[#9A968B] font-normal">
          [{String(accounts.length).padStart(2, "0")}]
        </span>
      </h1>

      {error && <p className="text-status-bad text-sm">{error}</p>}

      <div className="border border-[#3d3d3a]">
        {accounts.length === 0 ? (
          <p className="px-4 py-6 text-[#9A968B]">no accounts found.</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a] bg-[#1a1918]">
                <th className="px-4 py-2 font-normal">user</th>
                <th className="px-4 py-2 font-normal">account</th>
                <th className="px-4 py-2 font-normal">on</th>
                <th className="px-4 py-2 font-normal">grp</th>
                <th className="px-4 py-2 font-normal"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {accounts.map((a) => (
                <tr key={a.id} className="hover:bg-[#1f1e1d] transition-colors">
                  <td className="px-4 py-2 text-[#9A968B] text-sm">{a.user_email}</td>
                  <td className="px-4 py-2 text-[#f4f3ee]">{a.name}</td>
                  <td className="px-4 py-2">
                    {a.system_disabled ? (
                      <Bracket className="text-[#5a5850]">-</Bracket>
                    ) : (
                      <>
                        <span className="text-[#9A968B]">[</span>
                        <span className={a.enabled ? "text-status-ok" : "text-status-bad"}>
                          {a.enabled ? "x" : "\u00a0"}
                        </span>
                        <span className="text-[#9A968B]">]</span>
                      </>
                    )}
                  </td>
                  <td className="px-4 py-2 text-[#9A968B]">
                    {a.group_number != null ? String(a.group_number).padStart(2, "0") : "—"}
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <Link
                      href={`/admin/accounts/${a.id}/follow-targets`}
                      className="group transition-colors"
                    >
                      <Bracket className="text-[#9A968B] group-hover:text-[#d97757]">
                        follow-targets
                      </Bracket>
                    </Link>
                    <button
                      onClick={() => handleDelete(a)}
                      disabled={busy === a.id}
                      className="group disabled:opacity-50 transition-colors"
                    >
                      <Bracket className="text-status-bad group-hover:text-[#f4f3ee]">
                        {busy === a.id ? "..." : "delete"}
                      </Bracket>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  );
}
