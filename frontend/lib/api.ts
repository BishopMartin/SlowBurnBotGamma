const API_URL = "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Auth
export async function login(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_URL}/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new Error("Invalid credentials.");
  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function register(email: string, password: string, displayName?: string) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
}

export async function logout() {
  await request("/auth/jwt/logout", { method: "POST" }).catch(() => {});
  localStorage.removeItem("token");
}

export async function getMe() {
  return request<User>("/users/me");
}

// Accounts
export async function getAccounts() {
  return request<Account[]>("/accounts");
}

export async function createAccount(data: Partial<Account>) {
  return request<Account>("/accounts", { method: "POST", body: JSON.stringify(data) });
}

export async function updateAccount(id: string, data: Partial<Account>) {
  return request<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteAccount(id: string) {
  return request(`/accounts/${id}`, { method: "DELETE" });
}

export async function getAccountSettings(id: string) {
  return request<AccountSettings>(`/accounts/${id}/settings`);
}

export async function saveAccountSettings(id: string, data: Partial<AccountSettings>) {
  return request<AccountSettings>(`/accounts/${id}/settings`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// Bot
export async function getEntitlement() {
  return request<Entitlement>("/bot/entitlement");
}

// Admin
export async function adminListUsers() {
  return request<AdminUser[]>("/admin/users");
}

export async function adminSyncSubscription(userId: string) {
  return request(`/admin/users/${userId}/sync-subscription`, { method: "POST" });
}

export async function getAccountDatabase(id: string, page: number, pageSize = 100) {
  return request<{ total: number; page: number; page_size: number; items: FollowTarget[] }>(
    `/accounts/${id}/database?page=${page}&page_size=${pageSize}`
  );
}

export interface AccountStats {
  pending: number;
  complete: number;
  total: number;
  success: number;
  last_25: number | null;
  all_time: number | null;
}

export async function getAccountStats(id: string) {
  return request<AccountStats>(`/accounts/${id}/stats`);
}

export async function adminListAccounts() {
  return request<AdminAccount[]>("/admin/accounts");
}

export async function adminGetFollowTargets(accountId: string, page: number, pageSize = 100) {
  return request<{ total: number; page: number; page_size: number; items: FollowTarget[] }>(
    `/admin/accounts/${accountId}/follow-targets?page=${page}&page_size=${pageSize}`
  );
}

// Types
export interface User {
  id: string;
  email: string;
  display_name: string | null;
  plan_tier: string;
  is_active: boolean;
  is_superuser: boolean;
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  enabled: boolean;
  group_number: number | null;
  proxy_enabled: boolean;
  proxy_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActionBlock {
  enabled: boolean;
  type: string;
  target: string;
  fixed_count: number;
  variable_count: number;
}

export interface AccountSettings {
  id: string;
  account_id: string;
  schedule_days: string | null;
  schedule_start: string | null;
  schedule_end: string | null;
  delay_base_minutes: number;
  delay_random_minutes: number;
  max_runs_per_day: number;
  actions: ActionBlock[] | null;
  unfollow_days: number;
  list_tab: string | null;
  account_group: string | null;
  account_list_tab: string | null;
  topics: string | null;
  updated_at: string;
}

export interface Entitlement {
  active: boolean;
  plan_tier: string;
  current_period_end: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  display_name: string | null;
  plan_tier: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminAccount {
  id: string;
  user_id: string;
  user_email: string;
  name: string;
  enabled: boolean;
  group_number: number | null;
  created_at: string;
}

export interface FollowTarget {
  id: string;
  target_handle: string;
  source: string | null;
  status: string;
  follow_date: string | null;
  unfollow_date: string | null;
  follow_back: boolean | null;
}
