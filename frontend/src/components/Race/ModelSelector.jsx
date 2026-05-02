const MODELS = [
  { id: "analyst",    label: "The Analyst",    alias: "Claude Sonnet",  color: "#3266ad", specialty: "Registry-first · NCT/CTIS · Audit-ready" },
  { id: "hunter",     label: "The Hunter",     alias: "GPT-4o",         color: "#0F6E56", specialty: "Launch timing · First-mover · CDMO signals" },
  { id: "scanner",    label: "The Scanner",    alias: "Gemini Flash",   color: "#854F0B", specialty: "Global breadth · Emerging markets · WHO" },
  { id: "strategist", label: "The Strategist", alias: "Mistral Large",  color: "#534AB7", specialty: "Market access · Payer logic · Tender cycles" },
  { id: "challenger", label: "The Challenger", alias: "Llama 3.1 70B", color: "#993C1D", specialty: "Unconstrained · Max scope · Manufacturing signals" },
];

export default function ModelSelector({ selected, onToggle }) {
  return (
    <div>
      <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em",
                  color: "var(--color-text-secondary)", marginBottom: 10 }}>
        Select racers — min 2, max 5
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8 }}>
        {MODELS.map((m) => {
          const on = selected.includes(m.id);
          return (
            <div
              key={m.id}
              onClick={() => onToggle(m.id)}
              style={{
                cursor: "pointer", userSelect: "none",
                border: on ? `2px solid ${m.color}` : "0.5px solid var(--color-border-tertiary)",
                borderRadius: "var(--border-radius-lg)",
                padding: "0.75rem",
                background: on ? "var(--color-background-secondary)" : "var(--color-background-primary)",
              }}
            >
              <p style={{ fontSize: 10, color: "var(--color-text-secondary)", textTransform: "uppercase",
                          letterSpacing: "0.05em", margin: "0 0 2px" }}>{m.label}</p>
              <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 3px" }}>{m.alias}</p>
              <p style={{ fontSize: 11, color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.4 }}>{m.specialty}</p>
              {on && <p style={{ fontSize: 11, color: m.color, margin: "6px 0 0", fontWeight: 500 }}>✓ Selected</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
