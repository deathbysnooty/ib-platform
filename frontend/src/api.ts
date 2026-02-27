const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getMe: () => request<{ email: string; name: string; picture?: string }>("/api/auth/me"),

  googleLogin: (credential: string) =>
    request<{ user: { email: string; name: string; picture?: string } }>("/api/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential }),
    }),

  logout: () =>
    request("/api/auth/logout", { method: "POST" }),

  chat: (message: string) =>
    request<{ message: string; paper_groups: import("./types").PaperGroup[]; resource_files: import("./types").PaperFile[] }>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    }),

  summarize: (fileId: string) =>
    request<{ summary: string }>(`/api/papers/${fileId}/summarize`, { method: "POST" }),

  adminLogins: () =>
    request<{
      total_logins: number;
      users: { email: string; name: string; picture?: string; last_seen: string; login_count: number }[];
      recent: { id: number; email: string; name: string; logged_in_at: string; ip_address?: string }[];
    }>("/api/admin/logins"),

  downloadUrl: (fileId: string) => `${BASE}/api/papers/${fileId}/download`,
};
