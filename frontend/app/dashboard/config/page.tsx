"use client";

import { useEffect, useState } from "react";
import { getUserConfig, updateUserConfig, getIgnoreHandles, updateIgnoreHandles, UserConfig } from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { BracketCheckbox } from "@/lib/bracket-checkbox";
import { BracketInput } from "@/lib/bracket-input";
import { Dropdown } from "@/lib/dropdown";
import { NumberInput } from "@/lib/number-input";

const NOTICES_OPTIONS = [
  { value: "email", label: "email" },
  { value: "text", label: "text" },
  { value: "both", label: "both" },
];

const sectionCls = "border border-[#3d3d3a]";

function formatPhone(raw: string): string {
  const d = raw.replace(/\D/g, "").slice(0, 10);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `(${d.slice(0, 3)}) ${d.slice(3)}`;
  return `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
}

function stripPhone(formatted: string): string {
  return formatted.replace(/\D/g, "");
}

export default function ConfigPage() {
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  // Session settings
  const [likeSuggested, setLikeSuggested] = useState(false);
  const [likeSponsored, setLikeSponsored] = useState(false);
  const [skipLoginCheck, setSkipLoginCheck] = useState(false);
  const [loginTries, setLoginTries] = useState(3);

  // Notification settings
  const [noticesType, setNoticesType] = useState("email");
  const [noticesSession, setNoticesSession] = useState(true);
  const [noticesLogin, setNoticesLogin] = useState(true);
  const [loginNoticesType, setLoginNoticesType] = useState("email");
  const [loginNotifyEmail, setLoginNotifyEmail] = useState("");
  const [loginNotifyPhone, setLoginNotifyPhone] = useState("");
  const [notifyEmail, setNotifyEmail] = useState("");
  const [notifyPhone, setNotifyPhone] = useState("");

  // Ignore list
  const [skipPrivate, setSkipPrivate] = useState(false);
  const [ignoreHandles, setIgnoreHandles] = useState("");

  useEffect(() => {
    getUserConfig()
      .then((c) => {
        setConfig(c);
        setLikeSuggested(c.like_suggested);
        setLikeSponsored(c.like_sponsored);
        setSkipLoginCheck(c.skip_login_check);
        setLoginTries(c.login_tries);
        setNoticesType(c.notices_type);
        setNoticesSession(c.notices_session);
        setNoticesLogin(c.notices_login);
        setLoginNoticesType(c.login_notices_type);
        setLoginNotifyEmail(c.login_notify_email ?? "");
        setLoginNotifyPhone(c.login_notify_phone ?? "");
        setSkipPrivate(c.skip_private);
        setNotifyEmail(c.notify_email ?? "");
        setNotifyPhone(c.notify_phone ?? "");
      })
      .catch(() => {});
    getIgnoreHandles()
      .then((r) => setIgnoreHandles(r.handles.join(", ")))
      .catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setMsg("");
    try {
      const updated = await updateUserConfig({
        like_suggested: likeSuggested,
        like_sponsored: likeSponsored,
        skip_login_check: skipLoginCheck,
        login_tries: loginTries,
        notices_type: noticesType,
        notices_session: noticesSession,
        notices_login: noticesLogin,
        login_notices_type: loginNoticesType,
        login_notify_email: loginNotifyEmail || null,
        login_notify_phone: loginNotifyPhone || null,
        skip_private: skipPrivate,
        notify_email: notifyEmail || null,
        notify_phone: notifyPhone || null,
      });
      setConfig(updated);
      const handles = ignoreHandles.split(",").map((h) => h.trim()).filter(Boolean);
      const result = await updateIgnoreHandles(handles);
      setIgnoreHandles(result.handles.join(", "));
      setMsg("saved.");
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "save failed.");
    } finally {
      setSaving(false);
    }
  }

  if (!config) {
    return <div className="font-mono text-[#9A968B]">loading…</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      <h1 className="font-semibold text-[#f4f3ee]">Config</h1>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">session settings</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap">
          <BracketCheckbox label="Like Suggested" checked={likeSuggested} onChange={setLikeSuggested} />
          <BracketCheckbox label="Like Sponsored" checked={likeSponsored} onChange={setLikeSponsored} />
          <BracketCheckbox label="Skip Login Check" checked={skipLoginCheck} onChange={setSkipLoginCheck} />

          <span className="inline-flex items-center gap-0">
            <span className="text-[#9A968B]">{"login tries: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <NumberInput
              value={loginTries}
              onChange={(n) => setLoginTries(n || 1)}
              placeholder="3"
              max={10}
              maxLength={2}
            />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </span>
        </div>
      </div>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">notifications</div>

        <div className="px-4 grid items-center gap-x-3" style={{ gridTemplateColumns: "28ch auto auto auto" }}>
          <div className="py-2 border-b border-[#3d3d3a]"><BracketCheckbox label="Session Notification" checked={noticesSession} onChange={setNoticesSession} /></div>
          <div className="py-2 border-b border-[#3d3d3a] inline-flex items-center gap-0 pr-5">
            <span className="text-[#9A968B]">{"type: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <Dropdown value={noticesType} onChange={(v) => setNoticesType(v)} placeholder="----" options={NOTICES_OPTIONS} />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </div>
          <div className="py-2 border-b border-[#3d3d3a]"><BracketInput label="email" value={notifyEmail} onChange={setNotifyEmail} type="email" placeholder="email@example.com" width="20ch" /></div>
          <div className="py-2 border-b border-[#3d3d3a]"><BracketInput label="phone" value={formatPhone(notifyPhone)} onChange={(v) => setNotifyPhone(stripPhone(v))} type="tel" placeholder="(123) 456-7890" width="14ch" /></div>

          <div className="py-2"><BracketCheckbox label="Login/Error Notification" checked={noticesLogin} onChange={setNoticesLogin} /></div>
          <div className="py-2 inline-flex items-center gap-0 pr-5">
            <span className="text-[#9A968B]">{"type: "}</span>
            <span className="text-[#f4f3ee]">{"["}</span>
            <Dropdown value={loginNoticesType} onChange={(v) => setLoginNoticesType(v)} placeholder="----" options={NOTICES_OPTIONS} />
            <span className="text-[#f4f3ee]">{"]"}</span>
          </div>
          <div className="py-2"><BracketInput label="email" value={loginNotifyEmail} onChange={setLoginNotifyEmail} type="email" width="20ch" /></div>
          <div className="py-2"><BracketInput label="phone" value={formatPhone(loginNotifyPhone)} onChange={(v) => setLoginNotifyPhone(stripPhone(v))} type="tel" width="14ch" /></div>
        </div>
      </div>

      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] text-[#9A968B] bg-[#1a1918]">universal ignore</div>

        <div className="px-4 py-3 flex items-center gap-x-5 gap-y-2 flex-wrap">
          <BracketCheckbox label="Skip Private Accounts" checked={skipPrivate} onChange={setSkipPrivate} />
        </div>

        <div className="px-4 py-3 border-t border-[#3d3d3a]">
          <div className="text-[#9A968B] mb-1">skip/ignore account list</div>
          <textarea
            value={ignoreHandles}
            onChange={(e) => setIgnoreHandles(e.target.value)}
            placeholder="----"
            rows={9}
            className="w-full bg-transparent text-[#f4f3ee] placeholder-[#9A968B] outline-none font-mono border border-[#3d3d3a] px-2 py-1 focus:border-[#d97757] transition-colors resize-y"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="group disabled:opacity-50 transition-colors bg-[#2e2c2a] border border-[#555] px-2 py-0.5"
        >
          <Bracket className="text-[#d97757] group-hover:text-[#f4f3ee]">
            {saving ? "saving…" : "save"}
          </Bracket>
        </button>
        {msg && <span className="text-status-ok">{msg}</span>}
      </div>
    </div>
  );
}
