import { useState } from "react";
import RacePanel from "./components/Race/RacePanel.jsx";

const _stored = () =>
  localStorage.getItem("arena_access_key") ||
  import.meta.env.VITE_ACCESS_KEY ||
  "";

export default function App() {
  const [accessKey, setAccessKey] = useState(_stored);
  const [input,     setInput]     = useState("");

  const save = () => {
    const k = input.trim();
    if (!k) return;
    localStorage.setItem("arena_access_key", k);
    setAccessKey(k);
    setInput("");
  };

  const reset = () => {
    localStorage.removeItem("arena_access_key");
    setAccessKey("");
  };

  if (!accessKey) {
    return (
      <div style={{ maxWidth: 420, margin: "12vh auto", padding: "0 1.5rem" }}>
        <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                    letterSpacing: "0.08em", margin: "0 0 6px" }}>
          Biosimilar Surveillance Arena
        </p>
        <p style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 20px" }}>
          Enter access key
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            type="password"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            placeholder="Paste your access key…"
            style={{ flex: 1 }}
            autoFocus
          />
          <button onClick={save}>Enter →</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1024, margin: "0 auto", padding: "0 1.5rem" }}>
      <RacePanel accessKey={accessKey} onUnauthorized={reset} />
    </div>
  );
}
