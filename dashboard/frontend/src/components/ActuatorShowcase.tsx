"use client";

import { useState } from "react";
import { Simulated } from "@/lib/types";
import { sendSimulated } from "@/lib/api";

const SLATS = 7;
const FRAME_H = 160;
const MIN_SLAT_H = 3;
const MAX_GAP = Math.floor((FRAME_H - SLATS * MIN_SLAT_H) / (SLATS - 1));

export default function ActuatorShowcase({ simulated }: { simulated: Simulated }) {
  const blinds = simulated.blinds ?? 0;
  const ac = simulated.ac ?? "off";
  const [busy, setBusy] = useState<string | null>(null);

  async function send(key: string, fn: () => Promise<unknown>) {
    setBusy(key);
    try { await fn(); } catch { /* status-pill shows connection state */ } finally { setBusy(null); }
  }

  const slatGap = Math.round((blinds / 100) * MAX_GAP);
  const cooling = ac === "cooling";
  const idle = ac === "idle";

  return (
    <div className="actuator-showcase">

      {/* ── BLINDS ── */}
      <div className="panel showcase-panel">
        <div className="showcase-header">
          <div>
            <h2>Motorized Blinds</h2>
            <span className={`tag ${blinds === 0 ? "warn" : "good"}`}>
              {blinds === 0 ? "Closed" : blinds >= 100 ? "Fully Open" : `${blinds}% Open`}
            </span>
          </div>
          <span className="ai-badge">AI Controlled</span>
        </div>

        <div className="window-frame" style={{ height: FRAME_H }}>
          {/* sky visible through the gaps */}
          <div className="window-sky" style={{ opacity: (blinds / 100) * 0.7 }} />
          {/* slat grid */}
          <div
            className="slats-container"
            style={{ gap: `${slatGap}px` }}
          >
            {Array.from({ length: SLATS }).map((_, i) => (
              <div key={i} className="slat" />
            ))}
          </div>
        </div>

        <div className="btn-group" style={{ marginTop: 16 }}>
          <button
            className={`btn ${blinds >= 100 ? "active" : ""}`}
            disabled={busy === "blinds-open"}
            onClick={() => send("blinds-open", () => sendSimulated("blinds", { position: 100 }))}
          >Open</button>
          <button
            className={`btn ${blinds === 50 ? "active" : ""}`}
            disabled={busy === "blinds-half"}
            onClick={() => send("blinds-half", () => sendSimulated("blinds", { position: 50 }))}
          >Half</button>
          <button
            className={`btn ${blinds === 0 ? "active" : ""}`}
            disabled={busy === "blinds-close"}
            onClick={() => send("blinds-close", () => sendSimulated("blinds", { position: 0 }))}
          >Close</button>
        </div>
      </div>

      {/* ── AC UNIT ── */}
      <div className="panel showcase-panel">
        <div className="showcase-header">
          <div>
            <h2>AC Unit</h2>
            <span className={`tag ${cooling ? "good" : idle ? "warn" : ""}`}>
              {ac.charAt(0).toUpperCase() + ac.slice(1)}
            </span>
          </div>
          <span className="ai-badge">AI Controlled</span>
        </div>

        <div className={`ac-body ${cooling ? "ac-cooling" : idle ? "ac-idle" : "ac-off"}`}>
          {/* status LED */}
          <div
            className="ac-led"
            style={{
              background: cooling ? "var(--accent)" : idle ? "var(--warn)" : "var(--muted)",
              boxShadow: cooling ? "0 0 12px var(--accent)" : "none",
            }}
          />
          {/* brand strip */}
          <div className="ac-brand">SMART AC</div>
          {/* grille */}
          <div className="ac-grille">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="ac-line" />
            ))}
          </div>
          {/* animated airflow when cooling */}
          {cooling && (
            <div className="ac-airflow">
              {Array.from({ length: 8 }).map((_, i) => (
                <div
                  key={i}
                  className="air-particle"
                  style={{
                    left: `${6 + i * 12}%`,
                    animationDelay: `${(i * 0.18).toFixed(2)}s`,
                    animationDuration: `${0.9 + (i % 3) * 0.15}s`,
                  }}
                />
              ))}
            </div>
          )}
          {/* temperature readout */}
          <div className="ac-temp">
            {cooling ? "18°C" : idle ? "22°C" : "—"}
          </div>
        </div>

        <div className="btn-group" style={{ marginTop: 16 }}>
          <button
            className={`btn ${cooling ? "active" : ""}`}
            disabled={busy === "ac-cool"}
            onClick={() => send("ac-cool", () => sendSimulated("ac", { state: "cooling" }))}
          >❄️ Cooling</button>
          <button
            className={`btn ${idle ? "active" : ""}`}
            disabled={busy === "ac-idle"}
            onClick={() => send("ac-idle", () => sendSimulated("ac", { state: "idle" }))}
          >Idle</button>
          <button
            className={`btn ${ac === "off" ? "active" : ""}`}
            disabled={busy === "ac-off"}
            onClick={() => send("ac-off", () => sendSimulated("ac", { state: "off" }))}
          >Off</button>
        </div>
      </div>
    </div>
  );
}
