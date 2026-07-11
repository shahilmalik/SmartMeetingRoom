"use client";

import { RoomState } from "@/lib/types";

export default function HealthPanel({ state }: { state: RoomState }) {
  const health = state.health ?? 0;
  const occupied = Boolean(state.occupied);
  const breaches = state.breaches ?? [];

  const healthClass = health >= 80 ? "good" : health >= 50 ? "warn" : "bad";

  return (
    <div className="panel">
      <h2>Room Health</h2>
      <div className="health-ring">
        <div className="ring" style={{ ["--val" as string]: String(health) }}>
          <span className="num">{health}</span>
        </div>
        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <span className={`tag ${healthClass}`}>
              {health >= 80 ? "Healthy" : health >= 50 ? "Degraded" : "Critical"}
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

      <div style={{ marginTop: 18 }}>
        <div className="row">
          <span className="k">Active goal</span>
          <span className="v">{occupied ? "Comfort & health" : "Energy saving"}</span>
        </div>
        <div className="row">
          <span className="k">Threshold breaches</span>
          <span className="v">
            {breaches.length === 0 ? (
              <span className="tag good">None</span>
            ) : (
              breaches.map((b) => (
                <span key={b} className="tag bad" style={{ marginLeft: 4 }}>
                  {b}
                </span>
              ))
            )}
          </span>
        </div>
        <div className="row">
          <span className="k">Light status</span>
          <span className="v">{state.light_status ?? "unknown"}</span>
        </div>
      </div>
    </div>
  );
}
