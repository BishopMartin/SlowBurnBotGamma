"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { adminListAccounts, AdminAccount } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

export default function AdminAccountsPage() {
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);

  useEffect(() => {
    adminListAccounts().then(setAccounts).catch(() => {});
  }, []);

  return (
    <div className="space-y-4 font-mono">
      <h1 className="font-semibold text-[#f0eee6]">
        admin — accounts{" "}
        <span className="text-[#73726c] font-normal">
          [{String(accounts.length).padStart(2, "0")}]
        </span>
      </h1>

      <div className="border border-[#3d3d3a]">
        {accounts.length === 0 ? (
          <p className="px-4 py-6 text-[#73726c]">no accounts found.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
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
                  <td className="px-4 py-2 text-[#73726c] text-sm">{a.user_email}</td>
                  <td className="px-4 py-2 text-[#f0eee6]">{a.name}</td>
                  <td className="px-4 py-2">
                    <span className="text-[#73726c]">[</span>
                    <span className={a.enabled ? "text-green-400" : "text-red-400"}>
                      {a.enabled ? "x" : "\u00a0"}
                    </span>
                    <span className="text-[#73726c]">]</span>
                  </td>
                  <td className="px-4 py-2 text-[#73726c]">
                    {a.group_number != null ? String(a.group_number).padStart(2, "0") : "—"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link
                      href={`/admin/accounts/${a.id}/follow-targets`}
                      className="group transition-colors"
                    >
                      <Bracket className="text-[#73726c] group-hover:text-[#d97757]">
                        follow-targets
                      </Bracket>
                    </Link>
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
