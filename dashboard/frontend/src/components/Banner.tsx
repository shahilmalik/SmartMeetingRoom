"use client";

import { RoomState } from "@/lib/types";

interface Alert {
  key: string;
  level: "critical" | "warn";
  icon: string;
  text: string;
}

export default function Banner({ state }: { state: RoomState }) {
  const alerts: Alert[] = [];

  const noise = state.noise;
  if (state.noise_high) {
    alerts.push({
      key: "noise",
      level: "warn",
      icon: "🔊",
      text: `High noise${noise != null ? ` · ${Math.round(noise)}%` : ""} — not ideal for focused work. Consider addressing the source.`,
    });
  }

  const co2 = state.co2;
  if (co2 != null && co2 >= 1400) {
    alerts.push({
      key: "co2",
      level: "critical",
      icon: "🫁",
      text: `CO₂ critical · ${Math.round(co2)} ppm — ventilating to restore air quality.`,
    });
  } else if (co2 != null && co2 >= 1000) {
    alerts.push({
      key: "co2-warn",
      level: "warn",
      icon: "🫁",
      text: `CO₂ elevated · ${Math.round(co2)} ppm — fresh-air fan engaged.`,
    });
  }

  if (alerts.length === 0) return null;

  return (
    <div className="banner-stack">
      {alerts.map((a) => (
        <div key={a.key} className={`banner ${a.level}`} role="alert">
          <span className="banner-icon">{a.icon}</span>
          <span className="banner-text">{a.text}</span>
        </div>
      ))}
    </div>
  );
}
