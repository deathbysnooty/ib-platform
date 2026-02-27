import { useEffect } from "react";
import { api } from "../api";
import { User } from "../types";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: object) => void;
          renderButton: (element: HTMLElement | null, config: object) => void;
        };
      };
    };
  }
}

interface Props {
  onLogin: (user: User) => void;
}

const FEATURES = [
  { icon: "📄", text: "Instant access to IB past papers & markschemes" },
  { icon: "🤖", text: "AI-powered paper analysis — topics, difficulty & Section B breakdown" },
  { icon: "📊", text: "Grade boundaries for every session" },
  { icon: "📐", text: "Formula & data booklets" },
  { icon: "🔍", text: "Topic search — find papers by concept (e.g. complex numbers, waves)" },
];

export default function LoginPage({ onLogin }: Props) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    const init = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }: { credential: string }) => {
          try {
            const result = await api.googleLogin(credential);
            onLogin(result.user as User);
          } catch (e: unknown) {
            alert((e as Error).message || "Login failed. Please try again.");
          }
        },
      });
      window.google.accounts.id.renderButton(document.getElementById("google-btn"), {
        theme: "outline",
        size: "large",
        width: 280,
        text: "signin_with",
      });
    };

    init();
    const interval = setInterval(() => {
      if (window.google) {
        init();
        clearInterval(interval);
      }
    }, 200);
    return () => clearInterval(interval);
  }, [clientId, onLogin]);

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0f172a 100%)" }}>
      {/* Top bar */}
      <header className="px-8 py-5 flex items-center gap-3">
        <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 rounded-xl" style={{ background: "white" }}>
          <img src="/photon-logo.png" alt="Photon Academy" style={{ height: "32px", width: "auto" }} />
        </a>
      </header>

      {/* Main content */}
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-4xl flex flex-col lg:flex-row gap-8 items-center">

          {/* Left — feature list */}
          <div className="flex-1 text-left hidden lg:block">
            <h2 className="text-4xl font-bold text-white mb-3 leading-tight">
              Your IB Study<br />
              <span style={{ color: "#f59e0b" }}>Assistant</span>
            </h2>
            <p className="mb-6 text-base" style={{ color: "rgba(255,255,255,0.55)" }}>
              Everything you need for IB exam prep — powered by AI,<br />built by Photon Academy Singapore.
            </p>
            <ul className="space-y-3">
              {FEATURES.map((f) => (
                <li key={f.text} className="flex items-start gap-3">
                  <span className="text-lg mt-0.5">{f.icon}</span>
                  <span className="text-sm" style={{ color: "rgba(255,255,255,0.75)" }}>{f.text}</span>
                </li>
              ))}
            </ul>
            <a
              href="https://ibtuition.sg"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-6 text-xs hover:underline"
              style={{ color: "rgba(245,158,11,0.6)" }}
            >
              ibtuition.sg →
            </a>
          </div>

          {/* Right — login card */}
          <div className="w-full max-w-sm">
            <div className="rounded-2xl shadow-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(245,158,11,0.25)" }}>
              {/* Gold accent bar */}
              <div className="h-1 w-full" style={{ background: "linear-gradient(90deg, #f59e0b, #fcd34d, #f59e0b)" }} />

              <div className="px-8 py-8 text-center">
                {/* Logo */}
                <div className="flex justify-center mb-5">
                  <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="px-5 py-3 rounded-2xl shadow-lg" style={{ background: "white" }}>
                    <img src="/photon-logo.png" alt="Photon Academy" style={{ height: "48px", width: "auto" }} />
                  </a>
                </div>

                <h1 className="text-2xl font-bold text-white mb-1 tracking-tight">Photon IB Papers</h1>
                <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="text-xs hover:underline" style={{ color: "#f59e0b" }}>
                  Photon Academy Singapore
                </a>

                {/* Feature pills — visible on mobile only */}
                <div className="flex flex-wrap justify-center gap-1.5 mt-4 mb-5 lg:hidden">
                  {["Past Papers", "AI Analysis", "Grade Boundaries", "Topic Search"].map((tag) => (
                    <span key={tag} className="text-xs px-2.5 py-1 rounded-full" style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.25)" }}>
                      {tag}
                    </span>
                  ))}
                </div>

                <div id="google-btn" className="flex justify-center mb-4 mt-5" />

                <p className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
                  Sign in with any Google account.
                </p>
              </div>
            </div>

            {/* Footer */}
            <p className="text-center text-xs mt-4" style={{ color: "rgba(255,255,255,0.2)" }}>
              © Photon Academy ·{" "}
              <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ color: "rgba(255,255,255,0.35)" }}>
                ibtuition.sg
              </a>
            </p>
          </div>

        </div>
      </div>
    </div>
  );
}
