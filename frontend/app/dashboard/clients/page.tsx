"use client";

import { useEffect, useRef, useState } from "react";
import {
  createDesktopBuild,
  revokeDesktopBuild,
  listDesktopBuilds,
  getDesktopBuild,
  getDesktopBuildDownloadUrl,
  getDesktopBuildDownloadToken,
  getDesktopBuildsMeta,
  getLinuxBuildInstructions,
  getSubscriptionInfo,
  DesktopBuild,
  DesktopBuildConfig,
  DesktopBuildWithToken,
  LinuxBuildInstructions,
  SubscriptionInfo,
} from "@/lib/api";
import { Bracket } from "@/lib/bracket";
import { BracketInput } from "@/lib/bracket-input";
import { BracketCheckbox } from "@/lib/bracket-checkbox";

const DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36";

const DEFAULT_CONFIG: DesktopBuildConfig = {
  client_name: "",
  system_type: "windows",
  chrome_path: "PortableChrome\\chrome.exe",
  chrome_version: "143",
  chrome_user_data_dir_base: "PortableChrome",
  headless: false,
  detach: false,
  close_browser_session: false,
  close_browser_exit: false,
  bot_idle_delay: 5,
  bot_debug: false,
  system_user_agent: DEFAULT_USER_AGENT,
  add_arguments: [],
  api_url: "",
};

const DEFAULT_LINUX_CONFIG: DesktopBuildConfig = {
  client_name: "",
  system_type: "linux",
  chrome_path: "",         // Chrome is installed in the Docker image
  chrome_version: "",
  chrome_user_data_dir_base: "",
  headless: true,          // forced by backend; no visible Chrome window in container
  detach: false,
  close_browser_session: false,
  close_browser_exit: false,
  bot_idle_delay: 5,
  bot_debug: false,
  system_user_agent: DEFAULT_USER_AGENT,
  add_arguments: [],
  api_url: "",
};

const sectionCls = "border border-[#3d3d3a]";

function statusColor(status: string): string {
  if (status === "ready") return "text-status-ok";
  if (status === "failed" || status === "revoked") return "text-status-bad";
  return "text-[#E5C07B]";
}

function isActive(b: DesktopBuild) { return b.status === "queued" || b.status === "running"; }
function isExpired(b: DesktopBuild) { return new Date(b.download_expires_at) < new Date(); }

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function BuildForm({
  initial,
  onSubmit,
  onCancel,
  submitting,
  error,
  submitLabel = "request build",
}: {
  initial: DesktopBuildConfig;
  onSubmit: (cfg: DesktopBuildConfig) => void;
  onCancel: () => void;
  submitting: boolean;
  error: string | null;
  submitLabel?: string;
}) {
  const [cfg, setCfg] = useState<DesktopBuildConfig>(initial);
  function set<K extends keyof DesktopBuildConfig>(k: K, v: DesktopBuildConfig[K]) {
    setCfg((p) => ({ ...p, [k]: v }));
  }

  function switchPlatform(platform: "windows" | "linux") {
    if (platform === "linux") {
      setCfg((p) => ({ ...DEFAULT_LINUX_CONFIG, client_name: p.client_name, system_user_agent: p.system_user_agent, api_url: p.api_url }));
    } else {
      setCfg((p) => ({ ...DEFAULT_CONFIG, client_name: p.client_name, system_user_agent: p.system_user_agent, api_url: p.api_url }));
    }
  }

  const isLinux = cfg.system_type === "linux";
  const canSubmit = !submitting && (isLinux || cfg.chrome_path.trim().length > 0);

  return (
    <div className="px-4 py-3 space-y-2 bg-[#1a1918] border-t border-[#3d3d3a]">
      {/* Platform selector */}
      <div className="flex items-center gap-x-4 gap-y-2 flex-wrap">
        <button
          onClick={() => switchPlatform("windows")}
          className={`group cursor-pointer transition-colors ${cfg.system_type === "windows" ? "" : "opacity-50"}`}
        >
          <Bracket className={cfg.system_type === "windows" ? "text-[#f4f3ee]" : "text-[#9A968B] group-hover:text-[#f4f3ee]"}>windows</Bracket>
        </button>
        <button
          onClick={() => switchPlatform("linux")}
          className={`group cursor-pointer transition-colors ${cfg.system_type === "linux" ? "" : "opacity-50"}`}
        >
          <Bracket className={cfg.system_type === "linux" ? "text-[#f4f3ee]" : "text-[#9A968B] group-hover:text-[#f4f3ee]"}>linux / docker</Bracket>
        </button>
      </div>
      <div className="flex items-center gap-x-0 gap-y-2 flex-wrap">
        {!isLinux && (
          <BracketInput label="chrome version" value={cfg.chrome_version} onChange={(v) => set("chrome_version", v)} width="5ch" placeholder="143" />
        )}
        <BracketInput label="client name" value={cfg.client_name} onChange={(v) => set("client_name", v.slice(0, 15))} width="15ch" placeholder="my laptop" />
      </div>
      <div>
        <BracketInput label="user agent" value={cfg.system_user_agent} onChange={(v) => set("system_user_agent", v)} width="72ch" />
      </div>
      {!isLinux && (
        <div className="flex items-center gap-x-4 gap-y-2 flex-wrap">
          <BracketInput label="chrome path" value={cfg.chrome_path} onChange={(v) => set("chrome_path", v)} width="30ch" placeholder="\PortableChrome\chrome.exe" />
          <BracketInput label="user data dir" value={cfg.chrome_user_data_dir_base} onChange={(v) => set("chrome_user_data_dir_base", v)} width="22ch" placeholder="\PortableChrome\" />
        </div>
      )}
      <div className="flex items-center gap-x-5 gap-y-2 flex-wrap">
        {!isLinux && (
          <>
            <BracketCheckbox label="headless" checked={cfg.headless} onChange={(v) => set("headless", v)} />
            <BracketCheckbox label="detach" checked={cfg.detach} onChange={(v) => set("detach", v)} />
          </>
        )}
        <BracketCheckbox label="close on session end" checked={cfg.close_browser_session} onChange={(v) => set("close_browser_session", v)} />
        <BracketCheckbox label="close on exit" checked={cfg.close_browser_exit} onChange={(v) => set("close_browser_exit", v)} />
      </div>
      {isLinux && (
        <p className="text-[#9A968B] text-sm">Chrome is included in the Docker image. Run with <code className="text-[#E5C07B]">docker run -it</code> for the TUI.</p>
      )}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => onSubmit(cfg)}
          disabled={!canSubmit}
          className="group cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Bracket className="text-[#d97757] group-hover:text-[#f4f3ee]">{submitting ? "requesting…" : submitLabel}</Bracket>
        </button>
        <button onClick={onCancel} className="group cursor-pointer transition-colors">
          <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">cancel</Bracket>
        </button>
        {error && <span className="text-status-bad">{error}</span>}
      </div>
    </div>
  );
}

function versionGt(a: string, b: string): boolean {
  const parse = (v: string) => v.split(".").map((n) => parseInt(n, 10));
  const [am, ap] = parse(a);
  const [bm, bp] = parse(b);
  return am > bm || (am === bm && ap > bp);
}

export default function ClientPage() {
  const [builds, setBuilds] = useState<DesktopBuild[]>([]);
  const [subInfo, setSubInfo] = useState<SubscriptionInfo | null>(null);
  const [currentBotVersion, setCurrentBotVersion] = useState<string>("");
  const [botReleaseDate, setBotReleaseDate] = useState<string>("");
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [loading, setLoading] = useState(true);

  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [downloading, setDownloading] = useState<string | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);

  const [justCreated, setJustCreated] = useState<DesktopBuildWithToken | null>(null);
  const [copied, setCopied] = useState(false);

  const [linuxInstructions, setLinuxInstructions] = useState<(LinuxBuildInstructions & { buildId: string }) | null>(null);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const [pageError, setPageError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    try {
      const data = await listDesktopBuilds();
      setBuilds(data);
      setPageError(null);
    } catch (e: unknown) {
      setPageError(e instanceof Error ? e.message : "Failed to load builds.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    getSubscriptionInfo().then(setSubInfo).catch(() => {});
    getDesktopBuildsMeta().then((m) => {
      setCurrentBotVersion(m.current_bot_version);
      setBotReleaseDate(m.current_bot_release_date);
    }).catch(() => {});
  }, []);

  async function refreshAll() {
    await load();
    getSubscriptionInfo().then(setSubInfo).catch(() => {});
  }

  useEffect(() => {
    const active = builds.filter(isActive);
    if (active.length === 0) { if (pollRef.current) clearInterval(pollRef.current); return; }
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const updated = await Promise.all(active.map((b) => getDesktopBuild(b.id).catch(() => b)));
      setBuilds((prev) => prev.map((b) => updated.find((u) => u.id === b.id) ?? b));
    }, 10_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [builds]);

  const activeBuilds = builds
    .filter((b) => b.status !== "revoked")
    .sort((a, b) => a.client_id - b.client_id);

  const maxClients = subInfo?.max_clients ?? 0;
  const emptySlotCount = Math.max(0, maxClients - activeBuilds.length);

  function toggleExpand(key: string) {
    setExpandedKey((prev) => prev === key ? null : key);
    setFormError(null);
  }

  async function handleNewBuild(cfg: DesktopBuildConfig) {
    setFormSubmitting(true);
    setFormError(null);
    try {
      const result = await createDesktopBuild(cfg);
      setJustCreated(result);
      setExpandedKey(null);
      await refreshAll();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Build request failed.");
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleRebuildWithConfig(buildId: string, slotNumber: number, cfg: DesktopBuildConfig) {
    setFormSubmitting(true);
    setFormError(null);
    try {
      await revokeDesktopBuild(buildId);
      const result = await createDesktopBuild(cfg, slotNumber);
      setJustCreated(result);
      setExpandedKey(null);
      await refreshAll();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : "Rebuild failed.");
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleDownload(build: DesktopBuild) {
    const isLinux = (build.build_options as DesktopBuildConfig).system_type === "linux";
    if (isLinux) {
      setDownloading(build.id);
      try {
        const instructions = await getLinuxBuildInstructions(build.id);
        setLinuxInstructions({ ...instructions, buildId: build.id });
      } catch (e: unknown) {
        setPageError(e instanceof Error ? e.message : "Failed to fetch build instructions.");
      } finally {
        setDownloading(null);
      }
      return;
    }
    setDownloading(build.id);
    try {
      const dt = await getDesktopBuildDownloadToken(build.id);
      const url = getDesktopBuildDownloadUrl(build.id) + `?dt=${encodeURIComponent(dt)}`;
      window.location.href = url;
      await load();
    } catch (e: unknown) {
      setPageError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setDownloading(null);
    }
  }

  function copyCmd(text: string, key: string) {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedCmd(key);
      setTimeout(() => setCopiedCmd(null), 2000);
    });
  }

  async function handleRevoke(buildId: string) {
    if (confirmRevoke !== buildId) { setConfirmRevoke(buildId); return; }
    setConfirmRevoke(null);
    setRevoking(buildId);
    try {
      await revokeDesktopBuild(buildId);
      if (expandedKey === buildId) setExpandedKey(null);
      await refreshAll();
    } catch (e: unknown) {
      setPageError(e instanceof Error ? e.message : "Revoke failed.");
    } finally {
      setRevoking(null);
    }
  }

  function copyToken(token: string) {
    navigator.clipboard.writeText(token).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const currentStr = String(activeBuilds.length).padStart(2, "0");
  const maxStr = maxClients > 0 ? String(maxClients).padStart(2, "0") : "--";

  return (
    <div className="space-y-4 font-mono">
      <div className="flex items-baseline gap-3">
        <h1 className="font-semibold text-[#f4f3ee]">Clients</h1>
        <span className="text-[#9A968B]">
          -- <span className="text-[#f4f3ee]">[</span>
          <span className="text-[#E5C07B]">{loading ? "--" : currentStr}/{maxStr}</span>
          <span className="text-[#f4f3ee]">]</span>
        </span>
      </div>

      {!bannerDismissed && currentBotVersion && (
        <div className="border border-[#d97757] px-4 py-3 flex items-center gap-3 flex-wrap">
          <span className="text-[#f4f3ee]">
            BurnBotClient <span className="text-[#E5C07B]">v{currentBotVersion}</span>
            {botReleaseDate && <span className="text-[#9A968B]"> released {botReleaseDate}</span>}
            <span className="text-[#9A968B]"> — update any old versions!</span>
          </span>
          <button onClick={() => setBannerDismissed(true)} className="group cursor-pointer transition-colors ml-auto">
            <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">dismiss</Bracket>
          </button>
        </div>
      )}

      {justCreated && (
        <div className="border border-[#d97757] px-4 py-3 flex items-center gap-3 flex-wrap">
          <span className="text-[#f4f3ee]">client {justCreated.client_id}</span>
          {justCreated.status === "failed"
            ? <span className="text-status-bad ml-1">build failed — check token permissions.</span>
            : <span className="text-[#f4f3ee]"> queued.</span>}
          <span className="text-[#9A968B]">activation token:</span>
          <code className="text-[#E5C07B]">{justCreated.activation_token}</code>
          <button onClick={() => copyToken(justCreated.activation_token)} className="group cursor-pointer transition-colors">
            <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">{copied ? "copied!" : "copy"}</Bracket>
          </button>
          <button onClick={() => setJustCreated(null)} className="group cursor-pointer transition-colors ml-auto">
            <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">dismiss</Bracket>
          </button>
        </div>
      )}

      {linuxInstructions && (
        <div className="border border-[#3d3d3a] px-4 py-3 space-y-2 bg-[#1a1918]">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-[#f4f3ee]">docker commands — client {builds.find(b => b.id === linuxInstructions.buildId)?.client_id ?? ""}</span>
            <button onClick={() => setLinuxInstructions(null)} className="group cursor-pointer transition-colors ml-auto">
              <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">dismiss</Bracket>
            </button>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-[#9A968B]">pull:</span>
            <code className="text-[#E5C07B] break-all">{linuxInstructions.pull_cmd}</code>
            <button onClick={() => copyCmd(linuxInstructions.pull_cmd, "pull")} className="group cursor-pointer transition-colors">
              <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">{copiedCmd === "pull" ? "copied!" : "copy"}</Bracket>
            </button>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-[#9A968B]">run:</span>
            <code className="text-[#E5C07B] break-all">{linuxInstructions.run_cmd}</code>
            <button onClick={() => copyCmd(linuxInstructions.run_cmd, "run")} className="group cursor-pointer transition-colors">
              <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">{copiedCmd === "run" ? "copied!" : "copy"}</Bracket>
            </button>
          </div>
        </div>
      )}

      {pageError && <div className="text-status-bad">{pageError}</div>}

      {/* Builds / slots table */}
      <div className={sectionCls}>
        {loading && <div className="px-4 py-4 text-[#9A968B]">loading...</div>}

        {!loading && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-[#9A968B] border-b border-[#3d3d3a] bg-[#1a1918]">
                  <th className="px-4 py-2 font-normal whitespace-nowrap">client</th>
                  <th className="px-4 py-2 font-normal whitespace-nowrap">name</th>
                  <th className="px-4 py-2 font-normal whitespace-nowrap">platform</th>
                  <th className="px-4 py-2 font-normal whitespace-nowrap">build date</th>
                  <th className="px-4 py-2 font-normal whitespace-nowrap">status</th>
                  <th className="px-4 py-2 font-normal whitespace-nowrap">client ver</th>
                  <th className="px-4 py-2 font-normal w-full"></th>
                </tr>
              </thead>
              <tbody>
                {/* Filled slots */}
                {activeBuilds.map((build) => {
                  const cfg = build.build_options as DesktopBuildConfig;
                  const buildIsOutdated = !!(currentBotVersion && build.bot_version && versionGt(currentBotVersion, build.bot_version));
                  const canDownload = build.status === "ready" && !isExpired(build) && !buildIsOutdated;
                  const isExpanded = expandedKey === build.id;
                  return (
                    <>
                      <tr key={build.id} className="border-t border-[#3d3d3a] hover:bg-[#1f1e1d] transition-colors">
                        <td className="px-4 py-3 text-[#f4f3ee] whitespace-nowrap">#{String(build.client_id).padStart(2, "0")}</td>
                        <td className="px-4 py-3 text-[#9A968B] whitespace-nowrap">{cfg.client_name || "—"}</td>
                        <td className="px-4 py-3 text-[#9A968B] whitespace-nowrap">{cfg.system_type === "linux" ? "linux" : "windows"}</td>
                        <td className="px-4 py-3 text-[#9A968B] whitespace-nowrap">{fmtDate(build.created_at)}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {buildIsOutdated
                            ? <span className="text-status-bad">out-dated</span>
                            : <span className={statusColor(build.status)}>{build.status}</span>}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-[#9A968B]">
                            {build.bot_version ? `v${build.bot_version}` : (currentBotVersion ? `v${currentBotVersion}` : "—")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex gap-2 justify-end items-center">
                            {canDownload && (
                              <button onClick={() => handleDownload(build)} disabled={downloading === build.id} className="group cursor-pointer transition-colors disabled:opacity-40">
                                <Bracket className="text-[#9A968B] group-hover:text-[#f4f3ee]">
                                  {downloading === build.id ? "…" : cfg.system_type === "linux" ? "get commands" : "download"}
                                </Bracket>
                              </button>
                            )}
                            <button
                              onClick={() => handleRevoke(build.id)}
                              disabled={revoking === build.id}
                              className="group cursor-pointer transition-colors disabled:opacity-40"
                              onBlur={() => setConfirmRevoke(null)}
                            >
                              <Bracket className={confirmRevoke === build.id ? "text-[#E5C07B] group-hover:text-[#f4f3ee]" : "text-[#9A968B] group-hover:text-[#f4f3ee]"}>
                                {revoking === build.id ? "…" : confirmRevoke === build.id ? "confirm?" : "revoke"}
                              </Bracket>
                            </button>
                            <button onClick={() => toggleExpand(build.id)} className="group cursor-pointer transition-colors">
                              <Bracket className={isExpanded ? "text-[#f4f3ee] group-hover:text-[#9A968B]" : "text-[#9A968B] group-hover:text-[#f4f3ee]"}>settings/build</Bracket>
                            </button>
                          </div>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${build.id}-form`} className="border-t border-[#3d3d3a]">
                          <td colSpan={7} className="p-0">
                            <BuildForm
                              initial={cfg}
                              submitLabel="request re-build"
                              onSubmit={(newCfg) => handleRebuildWithConfig(build.id, build.client_id, newCfg)}
                              onCancel={() => { setExpandedKey(null); setFormError(null); }}
                              submitting={formSubmitting}
                              error={formError}
                            />
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}

                {/* Empty slots */}
                {Array.from({ length: emptySlotCount }).map((_, i) => {
                  const slotKey = `slot-${i}`;
                  const slotNum = activeBuilds.length + i + 1;
                  const isExpanded = expandedKey === slotKey;
                  return (
                    <>
                      <tr key={slotKey} className="border-t border-[#3d3d3a] hover:bg-[#1f1e1d] transition-colors">
                        <td className="px-4 py-3 text-[#3d3d3a]">#{String(slotNum).padStart(2, "0")}</td>
                        <td className="px-4 py-3 text-[#3d3d3a]">—</td>
                        <td className="px-4 py-3 text-[#3d3d3a]">—</td>
                        <td className="px-4 py-3 text-[#3d3d3a]">—</td>
                        <td className="px-4 py-3 text-[#3d3d3a]">—</td>
                        <td className="px-4 py-3 text-[#3d3d3a]">—</td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => toggleExpand(slotKey)} className="group cursor-pointer transition-colors">
                            <Bracket className={isExpanded ? "text-[#f4f3ee] group-hover:text-[#9A968B]" : "text-[#9A968B] group-hover:text-[#f4f3ee]"}>settings/build</Bracket>
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr key={`${slotKey}-form`} className="border-t border-[#3d3d3a]">
                          <td colSpan={7} className="p-0">
                            <BuildForm
                              initial={DEFAULT_CONFIG}
                              submitLabel="request build"
                              onSubmit={handleNewBuild}
                              onCancel={() => { setExpandedKey(null); setFormError(null); }}
                              submitting={formSubmitting}
                              error={formError}
                            />
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}

                {maxClients === 0 && !loading && (
                  <tr className="border-t border-[#3d3d3a]">
                    <td colSpan={7} className="px-4 py-4 text-[#9A968B]">No active subscription.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Getting started */}
      <div className={sectionCls}>
        <div className="px-4 py-2 border-b border-[#3d3d3a] bg-[#1a1918]">
          <span className="text-[#f4f3ee]">getting started</span>
        </div>
        <div className="px-4 py-4 space-y-4 text-[#9A968B]">
          <div className="space-y-1">
            <p className="text-[#f4f3ee]">windows</p>
            <p><span className="text-[#f4f3ee]">1.</span> Click <span className="text-[#f4f3ee]">settings/build</span> on an empty slot, select <span className="text-[#f4f3ee]">windows</span>, and configure your Chrome path.</p>
            <p><span className="text-[#f4f3ee]">2.</span> Download <code className="text-[#E5C07B]">SlowBurnBot.exe</code> when status shows <span className="text-status-ok">ready</span>.</p>
            <p><span className="text-[#f4f3ee]">3.</span> Run the EXE on Windows and log in with your dashboard credentials. Activates on first launch.</p>
          </div>
          <div className="space-y-1">
            <p className="text-[#f4f3ee]">linux / docker</p>
            <p><span className="text-[#f4f3ee]">1.</span> Click <span className="text-[#f4f3ee]">settings/build</span> on an empty slot, select <span className="text-[#f4f3ee]">linux / docker</span>.</p>
            <p><span className="text-[#f4f3ee]">2.</span> Click <span className="text-[#f4f3ee]">get commands</span> when status shows <span className="text-status-ok">ready</span> to see your <code className="text-[#E5C07B]">docker pull</code> and <code className="text-[#E5C07B]">docker run</code> commands.</p>
            <p><span className="text-[#f4f3ee]">3.</span> Run <code className="text-[#E5C07B]">docker run -it</code> on your Linux machine. Log in with your dashboard credentials. The TUI runs in your terminal.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
