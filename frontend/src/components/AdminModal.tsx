import { useEffect, useState } from "react";
import { api } from "../api";

interface Props {
  onClose: () => void;
}

interface UserRow {
  email: string;
  name: string;
  picture?: string;
  last_seen: string;
  login_count: number;
}

export default function AdminModal({ onClose }: Props) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [totalLogins, setTotalLogins] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"users" | "recent">("users");
  const [recent, setRecent] = useState<{ id: number; email: string; name: string; logged_in_at: string; ip_address?: string }[]>([]);

  useEffect(() => {
    api.adminLogins()
      .then((data) => {
        setTotalLogins(data.total_logins);
        setUsers(data.users);
        setRecent(data.recent);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("en-SG", { timeZone: "Asia/Singapore", dateStyle: "medium", timeStyle: "short" });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.6)" }}>
      <div className="w-full max-w-2xl rounded-2xl overflow-hidden shadow-2xl" style={{ background: "white", maxHeight: "85vh", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div className="px-6 py-4 flex items-center justify-between flex-shrink-0" style={{ background: "#0f172a", borderBottom: "2px solid #f59e0b" }}>
          <div>
            <h2 className="text-white font-semibold">Admin — Login Tracker</h2>
            {!loading && !error && (
              <p className="text-xs mt-0.5" style={{ color: "#f59e0b" }}>
                {users.length} unique users · {totalLogins} total logins
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-white opacity-60 hover:opacity-100 text-xl leading-none">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b flex-shrink-0" style={{ borderColor: "#e2e8f0" }}>
          {(["users", "recent"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="px-5 py-2.5 text-sm font-medium capitalize transition-colors"
              style={{
                borderBottom: tab === t ? "2px solid #f59e0b" : "2px solid transparent",
                color: tab === t ? "#0f172a" : "#94a3b8",
              }}
            >
              {t === "users" ? "Unique Users" : "Recent Logins"}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-4">
          {loading && <p className="text-sm text-center py-8" style={{ color: "#94a3b8" }}>Loading…</p>}
          {error && <p className="text-sm text-center py-8" style={{ color: "#ef4444" }}>{error}</p>}

          {!loading && !error && tab === "users" && (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>User</th>
                  <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>Last Seen</th>
                  <th className="text-right py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>Logins</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.email} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td className="py-2.5 px-2">
                      <div className="flex items-center gap-2">
                        {u.picture
                          ? <img src={u.picture} alt="" className="w-7 h-7 rounded-full flex-shrink-0" />
                          : <div className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold text-white" style={{ background: "#6366f1" }}>{u.name?.[0] || "?"}</div>
                        }
                        <div>
                          <p className="font-medium" style={{ color: "#0f172a" }}>{u.name}</p>
                          <p className="text-xs" style={{ color: "#94a3b8" }}>{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-2 text-xs" style={{ color: "#64748b" }}>{formatDate(u.last_seen)}</td>
                    <td className="py-2.5 px-2 text-right">
                      <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: "rgba(99,102,241,0.1)", color: "#4338ca" }}>
                        {u.login_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {!loading && !error && tab === "recent" && (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>User</th>
                  <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>Time (SGT)</th>
                  <th className="text-left py-2 px-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>IP</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td className="py-2 px-2">
                      <p className="font-medium" style={{ color: "#0f172a" }}>{r.name}</p>
                      <p className="text-xs" style={{ color: "#94a3b8" }}>{r.email}</p>
                    </td>
                    <td className="py-2 px-2 text-xs" style={{ color: "#64748b" }}>{formatDate(r.logged_in_at)}</td>
                    <td className="py-2 px-2 text-xs" style={{ color: "#94a3b8" }}>{r.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
