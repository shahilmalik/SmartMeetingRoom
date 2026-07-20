"use client";

import { useEffect, useRef, useState } from "react";
import { SensorOverrides, SensorReading } from "@/lib/types";
import { sendSensorOverrides } from "@/lib/api";

interface Props {
  sensors: Record<string, SensorReading>;
  overrides: SensorOverrides;
  daylight?: boolean;
  occupied?: boolean;
}

interface NumericSensor {
  id: string;
  label: string;
  icon: string;
  min: number;
  max: number;
  step: number;
  unit: string;
}

const NUMERIC: NumericSensor[] = [
  { id: "temperature", label: "Temperature", icon: "🌡️", min: 14, max: 34, step: 0.5, unit: "°C" },
  { id: "co2", label: "CO₂", icon: "🫁", min: 400, max: 2000, step: 50, unit: "ppm" },
  { id: "noise", label: "Noise", icon: "🔊", min: 0, max: 100, step: 1, unit: "%" },
  { id: "light", label: "Light", icon: "☀️", min: 0, max: 100, step: 1, unit: "%" },
  { id: "humidity", label: "Humidity", icon: "💧", min: 20, max: 80, step: 1, unit: "%" },
];

export default function SensorOverridePanel({ sensors, overrides, daylight, occupied }: Props) {
  const [held, setHeld] = useState<SensorOverrides>(overrides ?? {});
  const initialised = useRef(false);

  // Seed from the server's retained overrides once (so a page reload keeps holds).
  useEffect(() => {
    if (!initialised.current && overrides && Object.keys(overrides).length) {
      setHeld(overrides);
    }
    initialised.current = true;
  }, [overrides]);

  function push(next: SensorOverrides) {
    setHeld(next);
    sendSensorOverrides(next).catch(() => {});
  }

  function live(id: string, fallback: number): number {
    const v = sensors[id]?.value;
    return typeof v === "number" ? v : fallback;
  }

  function hold(id: string, value: number) {
    push({ ...held, [id]: value });
  }

  function release(id: string) {
    const next = { ...held };
    delete next[id];
    push(next);
  }

  function releaseAll() {
    push({});
  }

  const anyHeld = Object.keys(held).length > 0;

  return (
    <div className="panel">
      <div className="showcase-header">
        <div>
          <h2>Sensor Simulator</h2>
          <span className="hint">Hold any reading to test the room. Release to return to live data.</span>
        </div>
        <button className="btn small" disabled={!anyHeld} onClick={releaseAll}>
          Release all
        </button>
      </div>

      <div className="override-list">
        {NUMERIC.map((s) => {
          const isHeld = s.id in held;
          const value = isHeld ? held[s.id] : Math.round(live(s.id, s.min) * 10) / 10;
          return (
            <div key={s.id} className={`override-row ${isHeld ? "on" : ""}`}>
              <div className="override-top">
                <span className="override-name">
                  {s.icon} {s.label}
                </span>
                <span className="override-val">
                  {value}
                  <small>{s.unit}</small>
                  {isHeld ? <span className="held-tag">HELD</span> : <span className="live-tag">live</span>}
                </span>
              </div>
              <div className="override-ctl">
                <input
                  type="range"
                  min={s.min}
                  max={s.max}
                  step={s.step}
                  value={value}
                  onChange={(e) => hold(s.id, Number(e.target.value))}
                />
                <button
                  className={`btn small ${isHeld ? "danger" : ""}`}
                  onClick={() => (isHeld ? release(s.id) : hold(s.id, value))}
                >
                  {isHeld ? "Release" : "Hold"}
                </button>
              </div>
            </div>
          );
        })}

        {/* Occupancy — held as 0/1 */}
        <div className={`override-row ${"occupancy" in held ? "on" : ""}`}>
          <div className="override-top">
            <span className="override-name">🚶 Occupancy</span>
            <span className="override-val">
              {"occupancy" in held ? (held.occupancy ? "Occupied" : "Empty") : occupied ? "Occupied" : "Empty"}
              {"occupancy" in held ? <span className="held-tag">HELD</span> : <span className="live-tag">live</span>}
            </span>
          </div>
          <div className="btn-group">
            <button className={`btn small ${held.occupancy === 1 ? "active" : ""}`} onClick={() => hold("occupancy", 1)}>
              Occupied
            </button>
            <button className={`btn small ${held.occupancy === 0 ? "active" : ""}`} onClick={() => hold("occupancy", 0)}>
              Empty
            </button>
            <button className="btn small danger" disabled={!("occupancy" in held)} onClick={() => release("occupancy")}>
              Release
            </button>
          </div>
        </div>

        {/* Daylight — decides whether opening the blinds helps */}
        <div className={`override-row ${"daylight" in held ? "on" : ""}`}>
          <div className="override-top">
            <span className="override-name">🌇 Daylight outside</span>
            <span className="override-val">
              {"daylight" in held ? (held.daylight ? "Daytime" : "Night") : daylight ? "Daytime" : "Night"}
              {"daylight" in held ? <span className="held-tag">HELD</span> : <span className="live-tag">clock</span>}
            </span>
          </div>
          <div className="btn-group">
            <button className={`btn small ${held.daylight === 1 ? "active" : ""}`} onClick={() => hold("daylight", 1)}>
              ☀️ Day
            </button>
            <button className={`btn small ${held.daylight === 0 ? "active" : ""}`} onClick={() => hold("daylight", 0)}>
              🌙 Night
            </button>
            <button className="btn small danger" disabled={!("daylight" in held)} onClick={() => release("daylight")}>
              Release
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
