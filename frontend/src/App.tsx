import { useState, useEffect } from "react";
import LoginPage from "./components/LoginPage";
import ChatPage from "./components/ChatPage";
import { api } from "./api";
import { User } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getMe()
      .then((u) => setUser(u as User))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "#0f172a" }}>
        <div className="animate-spin w-10 h-10 rounded-full" style={{ border: "3px solid #f59e0b", borderTopColor: "transparent" }} />
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  return <ChatPage user={user} onLogout={() => setUser(null)} />;
}
