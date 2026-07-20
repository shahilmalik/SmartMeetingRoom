"use client";

import { RoomState } from "@/lib/types";

export default function HealthPanel({ state }: { state: RoomState }) {
  const health = state.health ?? 0;
  const occupied = Boolean(state.occupied);
  const factors = state.health_factors ?? [];

  const healthClass = health >= 80 ? "good" : health >= 50 ? "warn" : "bad";

  return (
    <div className="panel">
      <h2>Productivity Score</h2>
      <div className="health-ring">
        <div className="ring" style={{ ["--val" as string]: String(health) }}>
          <span className="num">{health}</span>
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <span className={`tag ${healthClass}`}>
              {health >= 80 ? "Productive" : health >= 50 ? "Degraded" : "Poor"}
            </span>
          </div>
          <div>
            <span className={`tag ${occupied ? "good" : "warn"}`}>
              {occupied ? "Occupied" : "Empty"}
            </span>
          </div>
          <div>
            <span className={`tag ${state.comfortable ? "good" : "bad"}`}>
              {state.comfortable ? "Comfortable" : "Action needed"}
            </span>
          </div>
        </div>
      </div>

      <div className="factor-list">
        {factors.map((f) => (
          <div className="factor" key={f.label}>
            <span className={`factor-dot ${f.ok ? "ok" : "bad"}`} />
            <span className="factor-label">{f.label}</span>
            <span className="factor-detail">{f.detail}</span>
            <span className={`factor-delta ${f.ok ? "" : "bad"}`}>
              {f.ok ? "✓" : `${f.delta}`}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="row">
          <span className="k">Active goal</span>
          <span className="v">{occupied ? "Comfort & productivity" : "Energy saving"}</span>
        </div>
        <div className="row">
          <span className="k">Light status</span>
          <span className="v">
            {state.light_status ?? "unknown"} · {state.daylight ? "☀️ daytime" : "🌙 night"}
          </span>
        </div>
      </div>
    </div>
  );
}
