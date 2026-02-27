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
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Card */}
          <div className="rounded-2xl shadow-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(245,158,11,0.25)" }}>
            {/* Gold accent bar */}
            <div className="h-1 w-full" style={{ background: "linear-gradient(90deg, #f59e0b, #fcd34d, #f59e0b)" }} />

            <div className="px-10 py-10 text-center">
              {/* Logo on white background */}
              <div className="flex justify-center mb-6">
                <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="px-5 py-3 rounded-2xl shadow-lg" style={{ background: "white" }}>
                  <img src="/photon-logo.png" alt="Photon Academy" style={{ height: "56px", width: "auto" }} />
                </a>
              </div>

              <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">For all your IB Needs</h1>
              <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="text-sm hover:underline" style={{ color: "#f59e0b" }}>
                ibtuition.sg
              </a>
              <p className="text-sm leading-relaxed mt-4 mb-8" style={{ color: "rgba(255,255,255,0.6)" }}>
                Best in Singapore and elsewhere
              </p>

              <div id="google-btn" className="flex justify-center mb-6" />

              <p className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>
                Sign in with any Google account.
              </p>
            </div>
          </div>

          {/* Footer note */}
          <p className="text-center text-xs mt-6" style={{ color: "rgba(255,255,255,0.25)" }}>
            © Photon Academy ·{" "}
            <a href="https://ibtuition.sg" target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ color: "rgba(255,255,255,0.4)" }}>
              ibtuition.sg
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
