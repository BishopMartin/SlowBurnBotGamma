"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  getAccounts,
  getAccountSettings,
  saveAccountSettings,
  updateAccount,
  deleteAccount,
  Account,
  AccountSettings,
  ActionBlock,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";

const ACTION_LABELS = ["1st", "2nd", "3rd", "4th"] as const;

const DEFAULT_ACTION: ActionBlock = {
  enabled: false,
  type: "",
  target: "",
  fixed_count: 0,
  variable_count: 0,
};

function pad4(actions: ActionBlock[] | null | undefined): ActionBlock[] {
  const base = actions ?? [];
  return [0, 1, 2, 3].map((i) => base[i] ?? { ...DEFAULT_ACTION });
}

const inputCls =
  "w-full bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors";

const sectionCls = "border border-[#3d3d3a]";

export default function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [settings, setSettings] = useState<Partial<AccountSettings>>({});
  const [actions, setActions] = useState<ActionBlock[]>(pad4(null));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getAccounts().then((list) => {
      const found = list.find((a) => a.id === id) ?? null;
      if (!found) { router.push("/dashboard/accounts"); return; }
      setAccount(found);
    });
    getAccountSettings(id)
      .then((s) => {
        setSettings(s);
        setActions(pad4(s.actions));
      })
      .catch(() => {});
  }, [id, router]);

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    try {
      await saveAccountSettings(id, { ...settings, actions });
      setMsg("saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "save failed.");
    } finally {
      setSaving(false);
    }
  }

  function updateAction(index: number, patch: Partial<ActionBlock>) {
    setActions((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)));
  }

  async function handleAccountField(patch: Partial<Account>) {
    const updated = await updateAccount(id, patch).catch(() => null);
    if (updated) setAccount(updated);
  }

  async function handleDelete() {
    if (!account) return;
    if (!confirm(`Delete account "${account.name}"?`)) return;
    await deleteAccount(id).catch(() => {});
    router.push("/dashboard/accounts");
  }

  if (!account) return null;

  const groupDisplay = account.group_number != null
    ? String(account.group_number).padStart(2, "0")
    : "";

  return (
    <div className="space-y-6 font-mono">
      {/* Header: ← accounts  theburleybar  [on]  group [01] */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/dashboard/accounts" className="text-[#73726c] hover:text-[#f0eee6] transition-colors">
          ← accounts
        </Link>
        <span className="text-[#f0eee6] font-semibold">{account.name}</span>
        <button
          onClick={() => handleAccountField({ enabled: !account.enabled })}
          className="group cursor-pointer transition-colors"
        >
          <Bracket className={account.enabled ? "text-green-400 group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
            {account.enabled ? "on" : "off"}
          </Bracket>
        </button>
        <div className="flex items-center gap-1">
          <span className="text-[#73726c]">group</span>
          <span className="text-[#f0eee6]">[</span>
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={2}
            placeholder="--"
            value={groupDisplay}
            onChange={(e) => {
              const val = e.target.value.replace(/\D/g, "").slice(0, 2);
              setAccount((a) => a && { ...a, group_number: val ? +val : null });
            }}
            onBlur={() => handleAccountField({ group_number: account.group_number })}
            className="w-5 bg-transparent text-[#f0eee6] outline-none text-center font-mono placeholder-[#73726c] border-none"
          />
          <span className="text-[#f0eee6]">]</span>
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-4">
        {/* Schedule */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">schedule</div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4 p-4">
            <div>
              <div className="text-[#73726c] mb-1">days</div>
              <input type="text" placeholder="e.g. daily"
                value={settings.schedule_days ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_days: e.target.value }))}
                className={inputCls} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">max runs / day</div>
              <input type="number" min={1}
                value={settings.max_runs_per_day ?? 1}
                onChange={(e) => setSettings((s) => ({ ...s, max_runs_per_day: +e.target.value }))}
                className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">start time</div>
              <input type="time"
                value={settings.schedule_start ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_start: e.target.value || null }))}
                className={inputCls} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">end time</div>
              <input type="time"
                value={settings.schedule_end ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_end: e.target.value || null }))}
                className={inputCls} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">delay base (min)</div>
              <input type="number" min={0}
                value={settings.delay_base_minutes ?? 60}
                onChange={(e) => setSettings((s) => ({ ...s, delay_base_minutes: +e.target.value }))}
                className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">delay random (min)</div>
              <input type="number" min={0}
                value={settings.delay_random_minutes ?? 0}
                onChange={(e) => setSettings((s) => ({ ...s, delay_random_minutes: +e.target.value }))}
                className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">actions</div>
          <div className="p-4 space-y-3">
            <div className="grid grid-cols-[3rem_3rem_1fr_1fr_4rem_4rem] gap-2 text-[#73726c]">
              <span></span>
              <span>on</span>
              <span>type</span>
              <span>target</span>
              <span className="text-center">#</span>
              <span className="text-center">?</span>
            </div>
            {actions.map((action, i) => (
              <div key={i} className="grid grid-cols-[3rem_3rem_1fr_1fr_4rem_4rem] gap-2 items-center">
                <span className="text-[#73726c]">{ACTION_LABELS[i]}</span>
                <button
                  type="button"
                  onClick={() => updateAction(i, { enabled: !action.enabled })}
                  className="group text-left cursor-pointer transition-colors"
                >
                  <Bracket className={action.enabled ? "text-[#f0eee6] group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                    {action.enabled ? "x" : "\u00a0"}
                  </Bracket>
                </button>
                <input type="text" placeholder="follow"
                  value={action.type}
                  onChange={(e) => updateAction(i, { type: e.target.value })}
                  className={inputCls} />
                <input type="text" placeholder="username / tag"
                  value={action.target}
                  onChange={(e) => updateAction(i, { target: e.target.value })}
                  className={inputCls} />
                <input type="number" min={0}
                  value={action.fixed_count}
                  onChange={(e) => updateAction(i, { fixed_count: +e.target.value })}
                  className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
                <input type="number" min={0}
                  value={action.variable_count}
                  onChange={(e) => updateAction(i, { variable_count: +e.target.value })}
                  className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
              </div>
            ))}
          </div>
        </div>

        {/* Follow Settings */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">follow settings</div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4 p-4">
            <div>
              <div className="text-[#73726c] mb-1">unfollow after (days)</div>
              <input type="number" min={1}
                value={settings.unfollow_days ?? 30}
                onChange={(e) => setSettings((s) => ({ ...s, unfollow_days: +e.target.value }))}
                className={`${inputCls} [appearance:textfield] [&::-webkit-inner-spin-button]:hidden [&::-webkit-outer-spin-button]:hidden`} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">list tab name</div>
              <input type="text" placeholder="e.g. list-MainLineBars"
                value={settings.list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, list_tab: e.target.value || null }))}
                className={inputCls} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">account group</div>
              <input type="text" placeholder="comma-separated"
                value={settings.account_group ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_group: e.target.value || null }))}
                className={inputCls} />
            </div>
            <div>
              <div className="text-[#73726c] mb-1">account list tab</div>
              <input type="text" placeholder="tab name"
                value={settings.account_list_tab ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_list_tab: e.target.value || null }))}
                className={inputCls} />
            </div>
            <div className="col-span-2">
              <div className="text-[#73726c] mb-1">topics</div>
              <input type="text" placeholder="comma-separated"
                value={settings.topics ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, topics: e.target.value || null }))}
                className={inputCls} />
            </div>
          </div>
        </div>

        {/* Save */}
        <div className="flex items-center gap-6">
          <button
            type="submit"
            disabled={saving}
            className="group disabled:opacity-50 transition-colors"
          >
            <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
              {saving ? "saving…" : "save settings"}
            </Bracket>
          </button>
          {msg && <span className="text-green-400">{msg}</span>}
          <button
            type="button"
            onClick={handleDelete}
            className="group transition-colors ml-auto"
          >
            <Bracket className="text-[#73726c] group-hover:text-red-400">delete account</Bracket>
          </button>
        </div>
      </form>
    </div>
  );
}
