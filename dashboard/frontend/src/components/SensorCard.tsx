"use client";

import { SensorReading } from "@/lib/types";

interface Props {
  label: string;
  icon: string;
  reading?: SensorReading;
  fallback?: string;
  max?: number;
}

export default function SensorCard({ label, icon, reading, fallback, max }: Props) {
  const value = reading?.value;
  const unit = reading?.unit ?? "";
  const display = value === undefined || value === null ? fallback ?? "--" : value;
  const pct =
    max && typeof value === "number" ? Math.max(0, Math.min(100, (value / max) * 100)) : null;

  return (
    <div className="card">
      <div className="icon">{icon}</div>
      <div className="label">{label}</div>
      <div className="value">
        {display}
        {unit && value !== undefined && value !== null ? <small>{unit}</small> : null}
      </div>
      {pct !== null ? (
        <div className="bar">
          <span style={{ width: `${pct}%` }} />
        </div>
      ) : null}
    </div>
  );
}
