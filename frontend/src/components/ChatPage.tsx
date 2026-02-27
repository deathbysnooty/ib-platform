import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { User, ChatMessage } from "../types";
import { api } from "../api";
import MessageBubble from "./MessageBubble";
import SummaryModal from "./SummaryModal";
import AdminModal from "./AdminModal";

interface Props {
  user: User;
  onLogout: () => void;
}

const EXAMPLE_QUERIES = [
  "Math AA HL May 2024 Paper 2",
  "Math AA HL Specimen Paper",
  "Math AA HL data booklet",
  "Math AA HL May 2023 grade boundaries",
  "Math AA HL papers with Section B on complex numbers",
];

export default function ChatPage({ user, onLogout }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `Hi ${user.name.split(" ")[0]}! Ask me for any IB past paper.\n\nTry something like:\n• "Math AA HL May 2024 Paper 2"\n• "Physics HL November 2023"\n• "Chemistry SL 2022"\n• "Math AA HL papers with Section B on complex numbers"\n• "Which Math AI SL papers have vectors?"\n\nYou can also ask for **grade boundaries** (e.g. "Math AA HL May 2023 grade boundaries") or **data booklets**.\n\nIf you don't specify a timezone, I'll return all available ones.`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [summaryFileId, setSummaryFileId] = useState<string | null>(null);
  const [showAdmin, setShowAdmin] = useState(false);
  const isAdmin = user.email === import.meta.env.VITE_ADMIN_EMAIL;
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const result = await api.chat(msg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.message, paper_groups: result.paper_groups, resource_files: result.resource_files },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry, something went wrong: ${(e as Error).message}` },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  async function handleLogout() {
    await api.logout();
    onLogout();
  }

  return (
    <div className="flex flex-col h-screen" style={{ background: "#f8fafc" }}>
      {/* ── Header ── */}
      <header style={{ background: "#0f172a", borderBottom: "2px solid #f59e0b" }} className="px-6 py-3 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-3">
          {/* White pill keeps logo visible on dark header */}
          <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="px-2.5 py-1 rounded-lg flex-shrink-0" style={{ background: "white" }}>
            <img src="/photon-logo.png" alt="Photon Academy" style={{ height: "28px", width: "auto" }} />
          </a>
          <div>
            <p className="text-xs" style={{ color: "#f59e0b" }}>For all your IB Needs · Powered by AI</p>
            <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="text-xs hover:underline" style={{ color: "rgba(245,158,11,0.55)" }}>
              ibtuition.sg
            </a>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {user.picture && (
            <img
              src={user.picture}
              alt={user.name}
              className="w-8 h-8 rounded-full"
              style={{ border: "2px solid #f59e0b" }}
            />
          )}
          <span className="text-sm text-white hidden sm:block">{user.name}</span>
          {isAdmin && (
            <button
              onClick={() => setShowAdmin(true)}
              className="text-xs px-3 py-1.5 rounded-lg transition-colors"
              style={{ color: "#94a3b8", border: "1px solid rgba(148,163,184,0.3)" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(148,163,184,0.1)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              Admin
            </button>
          )}
          <button
            onClick={handleLogout}
            className="text-xs px-3 py-1.5 rounded-lg transition-colors"
            style={{ color: "#f59e0b", border: "1px solid rgba(245,158,11,0.4)" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.1)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5 max-w-4xl w-full mx-auto">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} onSummarize={setSummaryFileId} />
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-sm" style={{ color: "#94a3b8" }}>
            <span className="flex gap-1">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{ background: "#f59e0b", animationDelay: `${delay}ms` }}
                />
              ))}
            </span>
            Searching papers…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* ── Input area ── */}
      <div className="bg-white border-t shadow-md px-4 py-4" style={{ borderColor: "#e2e8f0" }}>
        <div className="max-w-4xl mx-auto">
          {/* Example chips */}
          <div className="flex gap-2 mb-3 flex-wrap">
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                disabled={loading}
                className="text-xs px-3 py-1.5 rounded-full transition-colors disabled:opacity-50"
                style={{ background: "rgba(15,23,42,0.06)", color: "#0f172a", border: "1px solid rgba(15,23,42,0.15)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(245,158,11,0.12)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(15,23,42,0.06)")}
              >
                {q}
              </button>
            ))}
          </div>

          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask for a paper… e.g. Math AA HL May 2024"
              rows={1}
              disabled={loading}
              className="flex-1 border rounded-xl px-4 py-3 text-sm resize-none focus:outline-none disabled:bg-gray-50"
              style={{
                minHeight: "48px",
                maxHeight: "120px",
                borderColor: "#cbd5e1",
              }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "#f59e0b")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#cbd5e1")}
              onInput={(e) => {
                const t = e.currentTarget;
                t.style.height = "auto";
                t.style.height = `${Math.min(t.scrollHeight, 120)}px`;
              }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className="text-sm font-semibold px-5 py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
              style={{ background: "#f59e0b", color: "#0f172a" }}
              onMouseEnter={(e) => { if (!e.currentTarget.disabled) e.currentTarget.style.background = "#d97706"; }}
              onMouseLeave={(e) => (e.currentTarget.style.background = "#f59e0b")}
            >
              Send
            </button>
          </div>
          <p className="text-xs mt-2" style={{ color: "#94a3b8" }}>
            Press <kbd className="font-mono bg-gray-100 px-1 rounded">Enter</kbd> to send ·{" "}
            <kbd className="font-mono bg-gray-100 px-1 rounded">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>

      {/* ── Summary modal ── */}
      {summaryFileId && (
        <SummaryModal fileId={summaryFileId} onClose={() => setSummaryFileId(null)} />
      )}

      {/* ── Admin modal ── */}
      {showAdmin && <AdminModal onClose={() => setShowAdmin(false)} />}
    </div>
  );
}

