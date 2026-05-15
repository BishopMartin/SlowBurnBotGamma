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
    return <div className="font-mono text-base04">loading...</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-base05">Plan</h1>

      <div className="border border-base03">
        <div className="border-b border-base03 px-4 py-2 bg-base01">
          <span className="text-base05">current plan</span>
        </div>
        <div className="px-4 py-4 space-y-2">
          <div className="flex items-center gap-4">
            <span className="text-base04">tier</span>
            <span className="text-base05 font-semibold capitalize">{info.plan_tier}</span>
            {info.status === "active" || info.status === "trialing" ? (
              <span className="text-status-ok">{info.status}</span>
            ) : (
              <span className="text-status-bad">{info.status}</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-base04">accounts</span>
            <span className="text-base05">{info.current_accounts}/{info.max_accounts}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-base04">clients</span>
            <span className="text-base05">{info.current_clients}/{info.max_clients}</span>
          </div>
          {info.current_period_end && (
            <div className="flex items-center gap-4">
              <span className="text-base04">renewal</span>
              <span className="text-base05">{new Date(info.current_period_end).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </div>

      <div className="border border-base03">
        <div className="border-b border-base03 px-4 py-2 bg-base01">
          <span className="text-base05">available plans</span>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-base04 border-b border-base03 bg-base01">
              <th className="px-4 py-2 font-normal">tier</th>
              <th className="px-4 py-2 font-normal">price</th>
              <th className="px-4 py-2 font-normal">accounts</th>
              <th className="px-4 py-2 font-normal">clients</th>
              <th className="px-4 py-2 font-normal text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-base03">
            {info.tiers.map((tier) => {
              const isCurrent = tier.name === info.plan_tier;
              const isUpgrade = tier.max_accounts > info.max_accounts;
              return (
                <tr
                  key={tier.name}
                  className={`transition-colors ${isCurrent ? "bg-base02" : "hover:bg-base02"}`}
                >
                  <td className="px-4 py-3">
                    <span className={`capitalize font-semibold ${isCurrent ? "text-base09" : "text-base04"}`}>
                      {tier.name}
                    </span>
                  </td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-base05" : "text-base04"}`}>${tier.price}/mo</td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-base05" : "text-base04"}`}>{tier.max_accounts}</td>
                  <td className={`px-4 py-3 ${isCurrent ? "text-base05" : "text-base04"}`}>{tier.max_clients}</td>
                  <td className="px-4 py-3 text-right">
                    {isCurrent ? (
                      <Bracket className="text-base09">current plan</Bracket>
                    ) : isUpgrade ? (
                      <Bracket className="text-base04">upgrade</Bracket>
                    ) : (
                      <Bracket className="text-base04">downgrade</Bracket>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        </div>
      </div>

      <p className="text-base04 text-sm">
        To change your plan, please contact the administrator.
      </p>
    </div>
  );
}
