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
import { Dropdown } from "@/lib/dropdown";

// ── dropdown data ─────────────────────────────────────────────────────────────

const ACTION_TYPES = ["follow", "unfollow", "like"] as const;

const ACTION_TARGETS: Record<string, string[]> = {
  follow:    ["suggested users", "account list [followers]", "account list [following]"],
  unfollow:  ["previous follows"],
  like: ["posts [homepage]", "posts [topics]"],
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
  const [editingPw, setEditingPw] = useState(false);
  const [pwValue, setPwValue] = useState("");

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
        <div className="flex items-center gap-1">
          <span className="text-[#73726c]">password</span>
          {editingPw ? (
            <>
              <span className="text-[#f0eee6]">[</span>
              <input
                type="password"
                autoFocus
                value={pwValue}
                onChange={(e) => setPwValue(e.target.value)}
                onBlur={() => {
                  if (pwValue) handleAccountField({ ig_password: pwValue } as Partial<Account>);
                  setEditingPw(false);
                  setPwValue("");
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") { e.preventDefault(); (e.target as HTMLInputElement).blur(); }
                  if (e.key === "Escape") { setEditingPw(false); setPwValue(""); }
                }}
                className="w-24 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors"
              />
              <span className="text-[#f0eee6]">]</span>
            </>
          ) : (
            <button
              onClick={() => setEditingPw(true)}
              className="group cursor-pointer transition-colors"
            >
              <Bracket className={account.has_password ? "text-green-400 group-hover:text-[#d97757]" : "text-[#73726c] group-hover:text-[#d97757]"}>
                {account.has_password ? "set" : "----"}
              </Bracket>
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-4">

        {/* Schedule */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">schedule</div>
          <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm">

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"days: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <Dropdown
                value={settings.schedule_days ?? ""}
                onChange={(v) => setSettings((s) => ({ ...s, schedule_days: v || null }))}
                placeholder="----"
                options={[
                  { value: "", label: "----" },
                  ...SCHEDULE_DAYS.map((d) => ({ value: d, label: d })),
                ]}
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"start: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                value={editingStart ?? (settings.schedule_start ? formatTime(settings.schedule_start) : "")}
                onFocus={() => setEditingStart(settings.schedule_start ? formatTime(settings.schedule_start) : "")}
                onChange={(e) => setEditingStart(e.target.value)}
                onBlur={() => { setSettings((s) => ({ ...s, schedule_start: parseTime(editingStart ?? "") })); setEditingStart(null); }}
                placeholder="10:00 AM"
                style={{ width: "8ch" }}
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"end: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                value={editingEnd ?? (settings.schedule_end ? formatTime(settings.schedule_end) : "")}
                onFocus={() => setEditingEnd(settings.schedule_end ? formatTime(settings.schedule_end) : "")}
                onChange={(e) => setEditingEnd(e.target.value)}
                onBlur={() => { setSettings((s) => ({ ...s, schedule_end: parseTime(editingEnd ?? "") })); setEditingEnd(null); }}
                placeholder="10:00 PM"
                style={{ width: "8ch" }}
                className="bg-transparent text-[#f0eee6] outline-none font-mono min-w-0 px-0"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"delay fixed: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.delay_base_minutes != null ? String(settings.delay_base_minutes) : ""}
                onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) setSettings((s) => ({ ...s, delay_base_minutes: n })); }}
                placeholder="60"
                maxLength={2}
                className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"delay random: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.delay_random_minutes != null ? String(settings.delay_random_minutes) : ""}
                onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) setSettings((s) => ({ ...s, delay_random_minutes: n })); }}
                placeholder="0"
                maxLength={2}
                className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"sessions/day: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.max_runs_per_day != null ? String(settings.max_runs_per_day) : ""}
                onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) setSettings((s) => ({ ...s, max_runs_per_day: n || 1 })); }}
                placeholder="1"
                maxLength={2}
                className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
            </span>

          </div>
        </div>

        {/* Actions */}
        <div className={sectionCls}>
          <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#73726c]">session actions</div>
          <table className="w-full font-mono">
            <thead>
              <tr className="text-left text-[#73726c] border-b border-[#3d3d3a]">
                <th className="px-4 py-2 font-normal w-10"></th>
                <th className="px-4 py-2 font-normal w-10">on</th>
                <th className="px-4 py-2 font-normal">type</th>
                <th className="px-4 py-2 font-normal">target</th>
                <th className="px-4 py-2 font-normal w-28">fixed</th>
                <th className="px-4 py-2 font-normal w-28">random</th>
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
                      <Dropdown
                        value={action.type}
                        onChange={(v) => updateAction(i, { type: v })}
                        placeholder="----"
                        options={[
                          { value: "", label: "----" },
                          ...ACTION_TYPES.map((t) => ({ value: t, label: t })),
                        ]}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <Dropdown
                        value={action.target}
                        onChange={(v) => updateAction(i, { target: v })}
                        placeholder="----"
                        disabled={targets.length === 0}
                        options={[
                          { value: "", label: "----" },
                          ...targets.map((t) => ({ value: t, label: t })),
                        ]}
                      />
                    </td>
                    <td className="px-4 py-2">
                      <span className="inline-flex items-center gap-0">
                        <span className="text-[#f0eee6]">{"["}</span>
                        <input
                          type="text"
                          inputMode="numeric"
                          value={action.fixed_count > 0 ? String(action.fixed_count) : ""}
                          onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) updateAction(i, { fixed_count: n }); }}
                          placeholder="0"
                          maxLength={2}
                          className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
                        />
                        <span className="text-[#f0eee6]">{"]"}</span>
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className="inline-flex items-center gap-0">
                        <span className="text-[#f0eee6]">{"["}</span>
                        <input
                          type="text"
                          inputMode="numeric"
                          value={action.variable_count > 0 ? String(action.variable_count) : ""}
                          onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) updateAction(i, { variable_count: n }); }}
                          placeholder="0"
                          maxLength={2}
                          className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
                        />
                        <span className="text-[#f0eee6]">{"]"}</span>
                      </span>
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
          <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap text-sm border-b border-[#3d3d3a]">

            <span className="inline-flex items-center gap-0">
              <span className="text-[#73726c]">{"unfollow after: "}</span>
              <span className="text-[#f0eee6]">{"["}</span>
              <input
                type="text"
                inputMode="numeric"
                value={settings.unfollow_days != null ? String(settings.unfollow_days) : ""}
                onChange={(e) => { const n = parseNum(e.target.value); if (n <= 99) setSettings((s) => ({ ...s, unfollow_days: n || 30 })); }}
                placeholder="30"
                maxLength={2}
                className="w-5 bg-transparent border-b border-[#3d3d3a] text-[#f0eee6] outline-none focus:border-[#d97757] font-mono transition-colors placeholder-[#73726c] text-center"
              />
              <span className="text-[#f0eee6]">{"]"}</span>
              <span className="text-[#73726c]">{" days"}</span>
            </span>

          </div>
          <div className="px-4 py-3 grid grid-cols-2 gap-x-6 gap-y-4">
            <div>
              <div className="text-[#73726c] text-sm mb-1">account group</div>
              <textarea placeholder="comma-separated" rows={5}
                value={settings.account_group ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, account_group: e.target.value || null }))}
                className="w-full bg-transparent border border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] p-2 font-mono transition-colors resize-none break-words whitespace-pre-wrap"
              />
            </div>
            <div>
              <div className="text-[#73726c] text-sm mb-1">instagram topics</div>
              <textarea placeholder="comma-separated" rows={5}
                value={settings.topics ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, topics: e.target.value || null }))}
                className="w-full bg-transparent border border-[#3d3d3a] text-[#f0eee6] placeholder-[#73726c] outline-none focus:border-[#d97757] p-2 font-mono transition-colors resize-none break-words whitespace-pre-wrap"
              />
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
