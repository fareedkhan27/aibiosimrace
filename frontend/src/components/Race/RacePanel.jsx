import { useState, useEffect } from "react";
import { jsPDF } from "jspdf";
import ModelSelector from "./ModelSelector";

const MODEL_META = {
  analyst:    { label: "The Analyst",    alias: "Claude Sonnet",  color: "#3266ad" },
  hunter:     { label: "The Hunter",     alias: "GPT-4o",         color: "#0F6E56" },
  scanner:    { label: "The Scanner",    alias: "Gemini Flash",   color: "#854F0B" },
  strategist: { label: "The Strategist", alias: "Mistral Large",  color: "#534AB7" },
  challenger: { label: "The Challenger", alias: "Llama 3.1 70B", color: "#993C1D" },
};

// Models sometimes return fields as strings instead of arrays. Never throw on bad shapes.
const toArr = (v) => Array.isArray(v) ? v : (v != null ? [String(v)] : []);
const toStr = (v) => (v != null ? String(v) : "");

function formatBrief(d) {
  if (!d) return "No data extracted.";
  const pipe = toArr(d.pipeline);
  const sep  = "─".repeat(48);
  let t = "";
  t += `BRAND          ${d.brand || "—"}\n`;
  t += `INN            ${d.inn || "—"}\n`;
  t += `ORIGINATOR     ${d.originator || "—"}\n`;
  t += `MECHANISM      ${d.mechanism || "—"}\n`;
  t += `PATENT EXPIRY  ${d.patent_expiry || "Not identified"}\n`;
  t += `AREA           ${d.therapeutic_area || "—"}\n`;
  t += `CONFIDENCE     ${d.confidence || "—"}\n\n`;
  const competitors = toArr(d.competitors);
  if (competitors.length) {
    t += `REFERENCE COMPETITORS\n`;
    competitors.forEach((c) => { t += `  · ${toStr(c)}\n`; });
    t += "\n";
  }
  t += `BIOSIMILAR PIPELINE — ${pipe.length} developer(s) identified\n${sep}\n`;
  pipe.forEach((p) => {
    t += `\n${p.company || "Unknown"}\n`;
    t += `  Indications   ${toArr(p.indications).map(toStr).join(", ") || "—"}\n`;
    t += `  Phase         ${p.phase || "—"}\n`;
    if (p.trial_id && p.trial_id !== "null") t += `  Trial ID      ${p.trial_id}\n`;
    if (p.est_trial_completion) t += `  Trial end     ${p.est_trial_completion}\n`;
    const mkt = toArr(p.markets).map(toStr).join(", ") || "—";
    if (p.est_launch) t += `  Est. launch   ${p.est_launch}  |  Markets: ${mkt}\n`;
    else              t += `  Markets       ${mkt}\n`;
    t += `  Probability   ${p.probability}%  [${p.source || "—"}]\n`;
    if (p.note) t += `  Note          ${p.note}\n`;
  });
  t += `\n${sep}\nPROVENANCE\n`;
  toArr(d.provenance).forEach((s) => { t += `  · ${toStr(s)}\n`; });
  return t;
}

function exportPDF(brand, winnerAlias, briefText, aiInsight) {
  const doc        = new jsPDF();
  const pageH      = doc.internal.pageSize.getHeight();
  const margin     = 14;
  const maxY       = pageH - 14;
  const lineH      = 4.5;
  let y            = 20;

  const addLines = (lines, size) => {
    doc.setFontSize(size);
    for (const line of lines) {
      if (y > maxY) { doc.addPage(); y = 16; doc.setFontSize(size); }
      doc.text(line, margin, y);
      y += lineH;
    }
  };

  doc.setFontSize(14);
  doc.text(`Biosimilar Intelligence Brief: ${brand}`, margin, y);
  y += 8;
  doc.setFontSize(10);
  doc.text(`Winner: ${winnerAlias}  ·  ${new Date().toLocaleDateString()}`, margin, y);
  y += 10;

  addLines(doc.splitTextToSize(briefText, 182), 8);

  if (aiInsight) {
    y += 5;
    if (y > maxY) { doc.addPage(); y = 16; }
    doc.setFontSize(9);
    doc.setFont(undefined, "bold");
    doc.text("AI Insight — beyond the data", margin, y);
    doc.setFont(undefined, "normal");
    y += 5;
    addLines(doc.splitTextToSize(aiInsight, 182), 8);
  }

  doc.save(`biosimilar-brief-${brand.toLowerCase().replace(/\s+/g, "-")}.pdf`);
}

export default function RacePanel({ accessKey, onUnauthorized }) {
  const [brand,    setBrand]    = useState("");
  const [region,   setRegion]   = useState("");
  const [selected, setSelected] = useState(["analyst", "hunter", "scanner"]);
  const [racing,      setRacing]      = useState(false);
  const [result,      setResult]      = useState(null);
  const [error,       setError]       = useState(null);
  const [tab,         setTab]         = useState("brief");
  const [history,     setHistory]     = useState([]);
  const [raceHistory, setRaceHistory] = useState(null);
  const [histLoading, setHistLoading] = useState(false);

  const toggleModel = (id) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.length > 2 ? prev.filter((x) => x !== id) : prev;
      return prev.length < 5 ? [...prev, id] : prev;
    });
  };

  const loadHistory = async () => {
    setHistLoading(true);
    try {
      const resp = await fetch("/api/history?limit=20", {
        headers: { "x-access-key": accessKey },
      });
      if (resp.ok) {
        const data = await resp.json();
        setRaceHistory(data.items || []);
      }
    } catch (_) {
      // history is non-critical — silently fail
    } finally {
      setHistLoading(false);
    }
  };

  useEffect(() => { loadHistory(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const startRace = async () => {
    if (!brand.trim() || selected.length < 2) return;
    setRacing(true);
    setError(null);
    setResult(null);
    setTab("brief");
    try {
      const resp = await fetch("/api/race", {
        method:  "POST",
        headers: { "Content-Type": "application/json", "x-access-key": accessKey },
        body:    JSON.stringify({ brand, region, model_keys: selected }),
      });
      if (!resp.ok) {
        if (resp.status === 401 && onUnauthorized) { onUnauthorized(); return; }
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `API error ${resp.status}`);
      }
      const data = await resp.json();
      setResult(data);
      loadHistory();
      setHistory((prev) => {
        const updated = [...prev];
        (data.rankings || []).forEach((r) => {
          const idx = updated.findIndex((h) => h.model_key === r.model_key);
          if (idx >= 0) {
            updated[idx].races++;
            updated[idx].totalScore += r.score.total;
            if (r.model_key === data.winner) updated[idx].wins++;
          } else {
            updated.push({
              model_key:  r.model_key,
              races:      1,
              totalScore: r.score.total,
              wins:       r.model_key === data.winner ? 1 : 0,
            });
          }
        });
        return updated.sort((a, b) => b.wins - a.wins);
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setRacing(false);
    }
  };

  const winner     = result?.rankings?.find((r) => r.model_key === result.winner);
  const winnerMeta = winner ? MODEL_META[winner.model_key] : null;

  const _US_SIGNALS = ["us", "usa", "united states", "fda", "purple book"];
  const _EU_SIGNALS = ["eu", "europe", "european union", "ema", "uk", "mhra", "united kingdom"];
  const _isUSEU = (markets) => {
    const norm = toArr(markets).map((m) => toStr(m).toLowerCase());
    return norm.some((m) => [..._US_SIGNALS, ..._EU_SIGNALS].some((s) => m.includes(s)));
  };

  const launchedBiosimilars = (() => {
    if (!result) return { useu: [], row: [] };
    const useu = [], row = [];
    const seenUSEU = new Set(), seenROW = new Set();
    toArr(result.rankings).forEach((r) => {
      const alias = MODEL_META[r.model_key]?.alias;
      toArr(r.output?.pipeline).forEach((p) => {
        const phase = toStr(p.phase).toLowerCase();
        if (!phase.includes("launch") && !phase.includes("approved")) return;
        const key = toStr(p.company).toLowerCase().trim();
        if (!key) return;
        const entry = {
          key,
          company:     toStr(p.company) || "Unknown",
          phase:       toStr(p.phase),
          markets:     toArr(p.markets).map(toStr),
          indications: toArr(p.indications).map(toStr),
          sources:     [alias].filter(Boolean),
        };
        if (_isUSEU(p.markets)) {
          const ex = useu.find((e) => e.key === key);
          if (ex) { if (alias && !ex.sources.includes(alias)) ex.sources.push(alias); return; }
          if (!seenUSEU.has(key)) { seenUSEU.add(key); useu.push(entry); }
        } else {
          const ex = row.find((e) => e.key === key);
          if (ex) { if (alias && !ex.sources.includes(alias)) ex.sources.push(alias); return; }
          if (!seenROW.has(key)) { seenROW.add(key); row.push(entry); }
        }
      });
    });
    useu.sort((a, b) => a.company.localeCompare(b.company));
    row.sort((a, b) => a.company.localeCompare(b.company));
    return { useu, row };
  })();

  return (
    <div style={{ padding: "1.5rem 0" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.75rem" }}>
        <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 4px" }}>
          Biosimilar Surveillance Arena
        </p>
        <p style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>The AI Race</p>
        <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>
          Up to 5 models. One query. The smartest wins the title.
        </p>
      </div>

      {/* Model selector */}
      <div style={{ marginBottom: "1.5rem" }}>
        <ModelSelector selected={selected} onToggle={toggleModel} />
      </div>

      {/* Brand input + region + button */}
      <div style={{ display: "flex", gap: 8, marginBottom: "1.5rem", alignItems: "center" }}>
        <input
          type="text"
          value={brand}
          onChange={(e) => setBrand(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !racing && startRace()}
          placeholder="Enter brand name — e.g. Opdivo, Keytruda, Herceptin..."
          style={{ flex: 1, fontSize: 14 }}
          disabled={racing}
        />
        <select value={region} onChange={(e) => setRegion(e.target.value)} disabled={racing}
                style={{ fontSize: 14, padding: "0.5rem" }}>
          <option value="">Global</option>
          <option value="CEE">CEE</option>
          <option value="LATAM">LATAM</option>
          <option value="MEA">MEA</option>
          <option value="APAC">APAC</option>
        </select>
        <button onClick={startRace} disabled={racing || !brand.trim() || selected.length < 2}
                style={{ whiteSpace: "nowrap", fontSize: 14 }}>
          {racing ? "Racing..." : "Start the Race ↗"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: "0.75rem 1rem", background: "var(--color-background-danger)",
                      border: "0.5px solid var(--color-border-danger)", borderRadius: "var(--border-radius-md)",
                      color: "var(--color-text-danger)", fontSize: 14, marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {/* Racer lanes */}
      {(racing || result) && (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${selected.length}, minmax(0, 1fr))`, gap: 12, marginBottom: "1.5rem" }}>
          {selected.map((key) => {
            const meta      = MODEL_META[key];
            const rankEntry = result?.rankings?.find((r) => r.model_key === key);
            const isWinner  = result?.winner === key;
            return (
              <div key={key} style={{
                background:  isWinner ? "var(--color-background-secondary)" : "var(--color-background-primary)",
                border:      isWinner ? `1.5px solid ${meta.color}` : "0.5px solid var(--color-border-tertiary)",
                borderLeft:  `3px solid ${meta.color}`,
                borderRadius: "var(--border-radius-lg)",
                padding:     "1rem 1.25rem",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 2 }}>
                  <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.06em", margin: 0 }}>
                    {meta.label}
                  </p>
                  <span style={{
                    display: "inline-block", fontSize: 11, padding: "2px 8px",
                    borderRadius: "var(--border-radius-md)",
                    background:  rankEntry ? "var(--color-background-success)" : "var(--color-background-info)",
                    color:       rankEntry ? "var(--color-text-success)"       : "var(--color-text-info)",
                    border:      `0.5px solid ${rankEntry ? "var(--color-border-success)" : "var(--color-border-info)"}`,
                  }}>
                    {rankEntry ? `${rankEntry.elapsed?.toFixed(1) ?? "?"}s` : "Racing..."}
                  </span>
                </div>
                <p style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>{meta.alias}</p>
                <div style={{ height: 4, background: "var(--color-border-tertiary)", borderRadius: 2, overflow: "hidden", margin: "8px 0" }}>
                  <div style={{
                    height: "100%", borderRadius: 2, background: meta.color,
                    width: rankEntry ? "100%" : "72%",
                    transition: "width 0.6s ease",
                  }} />
                </div>
                {rankEntry && (
                  <>
                    <p style={{ fontSize: 22, fontWeight: 500, color: isWinner ? meta.color : "var(--color-text-primary)", margin: "4px 0 2px" }}>
                      {rankEntry.score?.total ?? 0} pts
                    </p>
                    <p style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: 0 }}>
                      {toArr(rankEntry.output?.pipeline).length} developers · {toArr(rankEntry.output?.provenance).length} sources
                    </p>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Winner banner */}
      {result && winner && winnerMeta && (
        <div style={{ background: "var(--color-background-secondary)", border: "0.5px solid var(--color-border-tertiary)",
                      borderRadius: "var(--border-radius-lg)", padding: "1.25rem", marginBottom: "1.5rem" }}>
          <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 6px" }}>
            Race complete — champion crowned
          </p>
          <p style={{ fontSize: 20, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 4px" }}>
            ★ {winnerMeta.label} ({winnerMeta.alias}) takes the title — {winner.score?.total} pts
          </p>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 12px" }}>
            {toArr(winner.output?.pipeline).length} biosimilar developers
            · {toArr(winner.output?.provenance).length} provenance sources
            · {toArr(winner.output?.pipeline).filter((p) => p.trial_id && p.trial_id !== "null").length} trial IDs
            · {winner.elapsed?.toFixed(1)}s
            {result.consensus && <span style={{ marginLeft: 8, color: winnerMeta.color, fontWeight: 500 }}>✓ Consensus</span>}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {Object.entries(winner.score?.bd || {}).map(([k, v]) => (
              <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12,
                                     padding: "3px 10px", borderRadius: "var(--border-radius-md)",
                                     background: "var(--color-background-primary)",
                                     border: "0.5px solid var(--color-border-tertiary)",
                                     color: "var(--color-text-secondary)" }}>
                <span style={{ fontWeight: 500, color: "var(--color-text-primary)" }}>{v}</span> {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Launched & Approved Globally — split US/EU vs Rest of World */}
      {result && (launchedBiosimilars.useu.length > 0 || launchedBiosimilars.row.length > 0) && (
        <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
                      borderRadius: "var(--border-radius-lg)", padding: "1.25rem", marginBottom: "1.5rem" }}>
          <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                      letterSpacing: "0.08em", margin: "0 0 16px" }}>
            Launched &amp; Approved Biosimilars — Globally ({launchedBiosimilars.useu.length + launchedBiosimilars.row.length})
          </p>

          {[
            { label: "US / EU", entries: launchedBiosimilars.useu, accent: "#1d4ed8" },
            { label: "Rest of World", entries: launchedBiosimilars.row, accent: "#6b7280" },
          ].map(({ label, entries, accent }) => entries.length > 0 && (
            <div key={label} style={{ marginBottom: "1.25rem" }}>
              <p style={{ fontSize: 11, fontWeight: 600, color: accent, textTransform: "uppercase",
                          letterSpacing: "0.06em", margin: "0 0 8px", display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: accent }} />
                {label} — {entries.length} compan{entries.length === 1 ? "y" : "ies"}
              </p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ color: "var(--color-text-secondary)", textAlign: "left" }}>
                    {["Company", "Phase", "Markets", "Indications", "Reported by"].map((h) => (
                      <th key={h} style={{ paddingBottom: 6, fontWeight: 500, paddingRight: 16, fontSize: 11 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => (
                    <tr key={e.key} style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                      <td style={{ padding: "7px 16px 7px 0", color: "var(--color-text-primary)", fontWeight: 500 }}>
                        {e.company}
                      </td>
                      <td style={{ padding: "7px 16px 7px 0" }}>
                        <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: "var(--border-radius-md)",
                                       background: "var(--color-background-success)", color: "var(--color-text-success)",
                                       border: "0.5px solid var(--color-border-success)", whiteSpace: "nowrap" }}>
                          {e.phase}
                        </span>
                      </td>
                      <td style={{ padding: "7px 16px 7px 0", color: "var(--color-text-secondary)" }}>
                        {e.markets.join(", ") || "—"}
                      </td>
                      <td style={{ padding: "7px 16px 7px 0", color: "var(--color-text-secondary)" }}>
                        {e.indications.slice(0, 2).join(", ")}
                        {e.indications.length > 2 && <span style={{ color: "var(--color-text-info)" }}> +{e.indications.length - 2}</span>}
                        {e.indications.length === 0 && "—"}
                      </td>
                      <td style={{ padding: "7px 0", color: "var(--color-text-secondary)", fontSize: 12 }}>
                        {e.sources.join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      {result && (
        <>
          <div style={{ display: "flex", gap: 4, marginBottom: 0, borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
            {[["brief", "Winner Brief"], ["all", "All Results"], ["leaderboard", "Session Leaderboard"]].map(([t, label]) => (
              <button key={t} onClick={() => setTab(t)} style={{
                fontSize: 13, padding: "6px 14px",
                borderRadius: "var(--border-radius-md) var(--border-radius-md) 0 0",
                background:   tab === t ? "var(--color-background-secondary)" : "transparent",
                border:       tab === t ? "0.5px solid var(--color-border-tertiary)" : "0.5px solid transparent",
                borderBottom: tab === t ? "1px solid var(--color-background-secondary)" : "none",
                color:        tab === t ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                cursor:       "pointer", marginBottom: -1,
              }}>
                {label}
              </button>
            ))}
          </div>

          {/* Winner Brief tab */}
          {tab === "brief" && winner && (
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
                          borderRadius: "0 var(--border-radius-lg) var(--border-radius-lg) var(--border-radius-lg)", padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
                <button
                  onClick={() => exportPDF(result.brand, winnerMeta.alias, formatBrief(winner.output), winner.output?.ai_insight)}
                  style={{ fontSize: 12, padding: "4px 12px", background: "var(--color-background-secondary)",
                           border: "0.5px solid var(--color-border-tertiary)", color: "var(--color-text-secondary)" }}>
                  Export PDF ↓
                </button>
              </div>
              <pre style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.9, whiteSpace: "pre-wrap",
                            color: "var(--color-text-primary)", margin: 0 }}>
                {formatBrief(winner.output)}
              </pre>
              {winner.output?.ai_insight && (
                <div style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)",
                              border: "0.5px solid var(--color-border-tertiary)", padding: "0.75rem 1rem", marginTop: "1rem" }}>
                  <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                              letterSpacing: "0.06em", margin: "0 0 6px", fontWeight: 500 }}>
                    AI Insight — beyond the data
                  </p>
                  <p style={{ fontSize: 13, color: "var(--color-text-primary)", margin: 0, lineHeight: 1.6 }}>
                    {winner.output.ai_insight}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* All Results tab */}
          {tab === "all" && (
            <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.min(result.rankings.length, 3)}, minmax(0, 1fr))`,
                          gap: 12, paddingTop: "1rem" }}>
              {result.rankings.map((r) => {
                const meta  = MODEL_META[r.model_key];
                const isWin = r.model_key === result.winner;
                return (
                  <div key={r.model_key} style={{
                    background:   "var(--color-background-primary)",
                    border:       "0.5px solid var(--color-border-tertiary)",
                    borderLeft:   `3px solid ${meta?.color}`,
                    borderRadius: "var(--border-radius-lg)", padding: "1rem",
                  }}>
                    <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                                letterSpacing: "0.06em", margin: "0 0 2px" }}>
                      {meta?.label} — {r.score?.total} pts {isWin && "★"}
                    </p>
                    <p style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", margin: "0 0 8px" }}>
                      {meta?.alias}
                    </p>
                    {r.error ? (
                      <p style={{ fontSize: 12, color: "var(--color-text-danger)", margin: 0 }}>Error: {r.error}</p>
                    ) : (
                      <pre style={{ fontFamily: "var(--font-mono)", fontSize: 11, lineHeight: 1.7,
                                    whiteSpace: "pre-wrap", color: "var(--color-text-secondary)", margin: 0,
                                    maxHeight: 520, overflowY: "auto" }}>
                        {formatBrief(r.output)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Session Leaderboard tab */}
          {tab === "leaderboard" && (
            <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)",
                          borderRadius: "0 var(--border-radius-lg) var(--border-radius-lg) var(--border-radius-lg)", padding: "1.25rem" }}>
              <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                          letterSpacing: "0.08em", margin: "0 0 12px" }}>
                Session Leaderboard
              </p>
              {history.length === 0 ? (
                <p style={{ fontSize: 14, color: "var(--color-text-secondary)", margin: 0 }}>No races yet this session.</p>
              ) : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: "var(--color-text-secondary)", textAlign: "left" }}>
                      {["Model", "Wins", "Races", "Avg Score"].map((h) => (
                        <th key={h} style={{ paddingBottom: 8, fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => {
                      const meta = MODEL_META[h.model_key];
                      return (
                        <tr key={h.model_key} style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                          <td style={{ padding: "8px 0", color: "var(--color-text-primary)", fontWeight: 500 }}>
                            <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                                           background: meta?.color, marginRight: 8 }} />
                            {meta?.alias}
                          </td>
                          <td style={{ padding: "8px 0", color: h.wins > 0 ? "var(--color-text-primary)" : "var(--color-text-secondary)" }}>
                            {h.wins}
                          </td>
                          <td style={{ padding: "8px 0", color: "var(--color-text-secondary)" }}>{h.races}</td>
                          <td style={{ padding: "8px 0", color: "var(--color-text-secondary)" }}>
                            {Math.round(h.totalScore / h.races)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}
      {/* Race History */}
      <div style={{ marginTop: "2.5rem", paddingTop: "1.5rem", borderTop: "0.5px solid var(--color-border-tertiary)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <p style={{ fontSize: 11, color: "var(--color-text-secondary)", textTransform: "uppercase",
                      letterSpacing: "0.08em", margin: 0 }}>
            Race History
          </p>
          <button onClick={loadHistory} disabled={histLoading}
                  style={{ fontSize: 11, padding: "3px 10px", background: "var(--color-background-secondary)",
                           border: "0.5px solid var(--color-border-tertiary)", color: "var(--color-text-secondary)" }}>
            {histLoading ? "Loading…" : "Refresh ↻"}
          </button>
        </div>

        {histLoading && raceHistory === null && (
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>Loading…</p>
        )}
        {!histLoading && raceHistory !== null && raceHistory.length === 0 && (
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>
            No races recorded yet. Results will appear here after each live race.
          </p>
        )}
        {raceHistory && raceHistory.length > 0 && (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ color: "var(--color-text-secondary)", textAlign: "left" }}>
                {["Date", "Brand", "Region", "Winner", "Score", "Models", "Time"].map((h) => (
                  <th key={h} style={{ paddingBottom: 8, fontWeight: 500, paddingRight: 16, fontSize: 11 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {raceHistory.map((h) => {
                const wMeta = MODEL_META[h.winner];
                return (
                  <tr key={h.id} style={{ borderTop: "0.5px solid var(--color-border-tertiary)" }}>
                    <td style={{ padding: "8px 16px 8px 0", color: "var(--color-text-secondary)", whiteSpace: "nowrap", fontSize: 12 }}>
                      {new Date(h.raced_at).toLocaleDateString()}{" "}
                      {new Date(h.raced_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td style={{ padding: "8px 16px 8px 0", color: "var(--color-text-primary)", fontWeight: 500 }}>
                      {h.brand}
                    </td>
                    <td style={{ padding: "8px 16px 8px 0", color: "var(--color-text-secondary)" }}>
                      {h.region || "Global"}
                    </td>
                    <td style={{ padding: "8px 16px 8px 0" }}>
                      {wMeta ? (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--color-text-primary)" }}>
                          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                                         background: wMeta.color, flexShrink: 0 }} />
                          {wMeta.alias}
                        </span>
                      ) : (h.winner || "—")}
                    </td>
                    <td style={{ padding: "8px 16px 8px 0", color: "var(--color-text-secondary)" }}>
                      {h.winner_score ?? "—"}
                    </td>
                    <td style={{ padding: "8px 16px 8px 0", color: "var(--color-text-secondary)" }}>
                      {h.model_keys.length}
                    </td>
                    <td style={{ padding: "8px 0", color: "var(--color-text-secondary)" }}>
                      {h.elapsed_s != null ? `${h.elapsed_s.toFixed(1)}s` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
