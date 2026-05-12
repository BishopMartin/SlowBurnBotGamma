"use client";

import { useEffect, useState } from "react";
import { getSubscriptionInfo, SubscriptionInfo } from "@/lib/api";
import { Bracket } from "@/lib/bracket";

export default function PlanPage() {
  const [info, setInfo] = useState<SubscriptionInfo | null>(null);

  useEffect(() => {
    getSubscriptionInfo().then(setInfo).catch(() => {});
  }, []);

  if (!info) {
    return <div className="font-mono text-[#9A968B]">loading...</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">Plan</h1>

      <div className="border border-[#3d3d3a]">
        <div className="border-b border-[#3d3d3a] px-4 py-2 bg-[#1a1918]">
          <span className="text-[#f4f3ee]">current plan</span>
        </div>
        <div className="px-4 py-4 space-y-2">
          <div className="flex items-center gap-4">
            <span className="text-[#9A968B]">tier</span>
            <span className="text-[#f4f3ee] font-semibold capitalize">{info.plan_tier}</span>
            {info.status === "active" || info.status === "trialing" ? (
              <span className="text-status-ok">{info.status}</span>
            ) : (
              <span className="text-status-bad">{info.status}</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[#9A968B]">accounts</span>
            <span className="text-[#f4f3ee]">{info.current_accounts}/{info.max_accounts}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[#9A968B]">clients</span>
            <span className="text-[#f4f3ee]">{info.current_clients}/{info.max_clients}</span>
          </div>
          {info.current_period_end && (
            <div className="flex items-center gap-4">
              <span className="text-[#9A968B]">renewal</span>
              <span className="text-[#f4f3ee]">{new Date(info.current_period_end).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </div>

      <div className="border border-[#3d3d3a]">
        <div className="border-b border-[#3d3d3a] px-4 py-2 bg-[#1a1918]">
          <span className="text-[#f4f3ee]">available plans</span>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a] bg-[#1a1918]">
              <th className="px-4 py-2 font-normal">tier</th>
              <th className="px-4 py-2 font-normal">price</th>
              <th className="px-4 py-2 font-normal">accounts</th>
              <th className="px-4 py-2 font-normal">clients</th>
              <th className="px-4 py-2 font-normal text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#3d3d3a]">
            {info.tiers.map((tier) => {
              const isCurrent = tier.name === info.plan_tier;
              const isUpgrade = tier.max_accounts > info.max_accounts;
              return (
                <tr
                  key={tier.name}
                  className={`transition-colors ${isCurrent ? "bg-[#1f1e1d]" : "hover:bg-[#1f1e1d]"}`}
                >
                  <td className="px-4 py-3">
                    <span className={`capitalize font-semibold ${isCurrent ? "text-[#d97757]" : "text-[#9A968B]"}`}>
                      {tier.name}
                    </span>
                  </td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-[#f4f3ee]" : "text-[#9A968B]"}`}>${tier.price}/mo</td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-[#f4f3ee]" : "text-[#9A968B]"}`}>{tier.max_accounts}</td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-[#f4f3ee]" : "text-[#9A968B]"}`}>{tier.max_clients}</td>
                  <td className="px-4 py-3 text-right">
                    {isCurrent ? (
                      <Bracket className="text-[#d97757]">current plan</Bracket>
                    ) : isUpgrade ? (
                      <Bracket className="text-[#9A968B]">upgrade</Bracket>
                    ) : (
                      <Bracket className="text-[#9A968B]">downgrade</Bracket>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>

      <p className="text-[#9A968B] text-sm">
        To change your plan, please contact the administrator.
      </p>
    </div>
  );
}
