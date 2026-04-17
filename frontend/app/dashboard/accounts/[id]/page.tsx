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
import { formatTime } from "@/lib/format";

// ── dropdown data ─────────────────────────────────────────────────────────────

const ACTION_TYPES = ["follow", "unfollow", "like post"] as const;

const ACTION_TARGETS: Record<string, string[]> = {
  follow:    ["suggested users", "account list [followers]", "account list [following]"],
  unfollow:  ["previous follows"],
  "like post": ["posts [homepage]", "posts [topics]"],
};

const SCHEDULE_DAYS = ["daily", "weekdays", "weekends"];

// ── helpers ───────────────────────────────────────────────────────────────────

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

/** Convert "10:00 PM" / "10:00PM" → "22:00"; pass through 24h as-is */
function parseTime(v: string): string | null {
  if (!v.trim()) return null;
  const m12 = v.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)$/i);
  if (m12) {
    let h = parseInt(m12[1], 10);
    const m = parseInt(m12[2], 10);
    if (m12[3].toUpperCase() === "PM" && h !== 12) h += 12;
    if (m12[3].toUpperCase() === "AM" && h === 12) h = 0;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }
  return v.slice(0, 5) || null;
}

/** Parse a numeric text field; empty → 0 */
function parseNum(v: string): number {
  const n = parseInt(v.replace(/[^0-9]/g, ""), 10);
  return isNaN(n) ? 0 : n;
}

// ── styles ────────────────────────────────────────────────────────────────────

const inputCls =
  "w-full bg-transparent border-b border-[#2a2a27] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] py-1 font-mono transition-colors";

const numInputCls =
  "w-full bg-transparent border-b border-[#2a2a27] text-[#f0eee6] outline-none focus:border-[#d97757] py-1 font-mono transition-colors";

const selectCls =
  "w-full bg-[#141413] border-b border-[#2a2a27] text-[#f0eee6] outline-none focus:border-[#d97757] py-1 font-mono transition-colors cursor-pointer appearance-none";

const sectionCls = "border border-[#3d3d3a]";

// ── component ─────────────────────────────────────────────────────────────────

export default function AccountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [settings, setSettings] = useState<Partial<AccountSettings>>({});
  const [actions, setActions] = useState<ActionBlock[]>(pad4(null));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [editingStart, setEditingStart] = useState<string | null>(null);
  const [editingEnd, setEditingEnd] = useState<string | null>(null);

  useEffect(() => {
    getAccounts().then((list) => {
      const found = list.find((a) => a.id === id) ?? null;
      if (!found) { router.push("/dashboard/accounts"); return; }
      setAccount(found);
    });
    getAccountSettings(id)
      .then((s) => { setSettings(s); setActions(pad4(s.actions)); })
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
    setActions((prev) => prev.map((a, i) => {
      if (i !== index) return a;
      const updated = { ...a, ...patch };
      // reset target when type changes
      if (patch.type !== undefined && patch.type !== a.type) updated.target = "";
      return updated;
    }));
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

  const groupDisplay = account.group_number != null ? String(account.group_number) : "";

  return (
    <div className="space-y-6 font-mono">

      {/* Header */}
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
            maxLength={2}
            placeholder="--"
            value={groupDisplay}
            onChange={(e) => {
              const val = e.target.value.replace(/\D/g, "").slice(0, 2);
              setAccount((a) => a && { ...a, group_number: val ? +val : null });
            }}
            onBlur={() => handleAccountField({ group_number: account.group_number })}
            className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
          />
          <span className="text-[#f0eee6]">]</span>
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-4">

        {/* Schedule */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">schedule</div>
          <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">days </span>
              <span className="text-[#f0eee6]">[ </span>
              <select
                value={settings.schedule_days ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_days: e.target.value || null }))}
                className="bg-transparent text-[#f0eee6] outline-none font-mono cursor-pointer"
              >
                <option value="">——</option>
                {SCHEDULE_DAYS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
              <span className="text-[#f0eee6]"> ]</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">start </span>
              <span className="text-[#f0eee6]">[ </span>
              <input
                type="text"
                size={8}
                value={editingStart ?? (settings.schedule_start ? formatTime(settings.schedule_start) : "")}
                onFocus={() => setEditingStart(settings.schedule_start ? formatTime(settings.schedule_start) : "")}
                onChange={(e) => setEditingStart(e.target.value)}
                onBlur={() => { setSettings((s) => ({ ...s, schedule_start: parseTime(editingStart ?? "") })); setEditingStart(null); }}
                placeholder="10:00 AM"
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]"> ]</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">end </span>
              <span className="text-[#f0eee6]">[ </span>
              <input
                type="text"
                size={8}
                value={editingEnd ?? (settings.schedule_end ? formatTime(settings.schedule_end) : "")}
                onFocus={() => setEditingEnd(settings.schedule_end ? formatTime(settings.schedule_end) : "")}
                onChange={(e) => setEditingEnd(e.target.value)}
                onBlur={() => { setSettings((s) => ({ ...s, schedule_end: parseTime(editingEnd ?? "") })); setEditingEnd(null); }}
                placeholder="10:00 PM"
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]"> ]</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"delay fixed "}</span>
              <span className="text-[#f0eee6]">{`[\u00a0`}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.delay_base_minutes != null ? String(settings.delay_base_minutes) : ""}
                onChange={(e) => setSettings((s) => ({ ...s, delay_base_minutes: parseNum(e.target.value) }))}
                placeholder="60"
                style={{ width: `${Math.max(String(settings.delay_base_minutes ?? "").length || 2, 2) + 1}ch` }}
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]">{`\u00a0]`}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"delay random "}</span>
              <span className="text-[#f0eee6]">{`[\u00a0`}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.delay_random_minutes != null ? String(settings.delay_random_minutes) : ""}
                onChange={(e) => setSettings((s) => ({ ...s, delay_random_minutes: parseNum(e.target.value) }))}
                placeholder="0"
                style={{ width: `${Math.max(String(settings.delay_random_minutes ?? "").length || 2, 2) + 1}ch` }}
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]">{`\u00a0]`}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"runs/day "}</span>
              <span className="text-[#f0eee6]">{`[\u00a0`}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.max_runs_per_day != null ? String(settings.max_runs_per_day) : ""}
                onChange={(e) => setSettings((s) => ({ ...s, max_runs_per_day: parseNum(e.target.value) || 1 }))}
                placeholder="1"
                style={{ width: `${Math.max(String(settings.max_runs_per_day ?? "").length || 1, 1) + 1}ch` }}
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]"> ]</span>
            </span>

          </div>
        </div>

        {/* Actions */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">actions</div>
          <table className="w-full font-mono">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <th className="px-4 py-2 font-normal w-10"></th>
                <th className="px-4 py-2 font-normal w-10">on</th>
                <th className="px-4 py-2 font-normal">type</th>
                <th className="px-4 py-2 font-normal">target</th>
                <th className="px-4 py-2 font-normal w-16">set</th>
                <th className="px-4 py-2 font-normal w-16">random</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#3d3d3a]">
              {actions.map((action, i) => {
                const targets = action.type ? (ACTION_TARGETS[action.type] ?? []) : [];
                return (
                  <tr key={i}>
                    <td className="px-4 py-2 text-[#73726c]">{ACTION_LABELS[i]}</td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={() => updateAction(i, { enabled: !action.enabled })}
                        className="group text-left cursor-pointer transition-colors"
                      >
                        <Bracket className={action.enabled ? "text-[#f0eee6] group-hover:text-red-400" : "text-[#73726c] group-hover:text-green-400"}>
                          {action.enabled ? "x" : "\u00a0"}
                        </Bracket>
                      </button>
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={action.type}
                        onChange={(e) => updateAction(i, { type: e.target.value })}
                        className={selectCls}
                      >
                        <option value="">—</option>
                        {ACTION_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <select
                        value={action.target}
                        onChange={(e) => updateAction(i, { target: e.target.value })}
                        disabled={targets.length === 0}
                        className={`${selectCls} disabled:text-[#3d3d3a] disabled:cursor-default`}
                      >
                        <option value="">—</option>
                        {targets.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={action.fixed_count > 0 ? String(action.fixed_count) : ""}
                        onChange={(e) => updateAction(i, { fixed_count: parseNum(e.target.value) })}
                        placeholder="0"
                        className={numInputCls}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text"
                        inputMode="numeric"
                        value={action.variable_count > 0 ? String(action.variable_count) : ""}
                        onChange={(e) => updateAction(i, { variable_count: parseNum(e.target.value) })}
                        placeholder="0"
                        className={numInputCls}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Follow Settings */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">follow settings</div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4 p-4">
            <div>
              <div className="text-[#73726c] mb-1">unfollow after (days)</div>
              <input
                type="text"
                inputMode="numeric"
                value={settings.unfollow_days != null ? String(settings.unfollow_days) : ""}
                onChange={(e) => setSettings((s) => ({ ...s, unfollow_days: parseNum(e.target.value) || 30 }))}
                placeholder="30"
                className={numInputCls}
              />
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

        {/* Save / Delete */}
        <div className="flex items-center gap-6">
          <button type="submit" disabled={saving} className="group disabled:opacity-50 transition-colors">
            <Bracket className="text-[#d97757] group-hover:text-[#f0eee6]">
              {saving ? "saving…" : "save settings"}
            </Bracket>
          </button>
          {msg && <span className="text-green-400">{msg}</span>}
          <button type="button" onClick={handleDelete} className="group transition-colors ml-auto">
            <Bracket className="text-[#73726c] group-hover:text-red-400">delete account</Bracket>
          </button>
        </div>

      </form>
    </div>
  );
}
