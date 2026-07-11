"use client";

import { useState } from "react";
import { Actuators, Simulated } from "@/lib/types";
import {
  sendLed,
  sendManualOverride,
  sendRelay,
  sendSimulated,
} from "@/lib/api";

interface Props {
  actuators: Actuators;
  simulated: Simulated;
}

export default function Controls({ actuators, simulated }: Props) {
  const [brightness, setBrightness] = useState<number>(actuators.led ?? 0);
  const [busy, setBusy] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<unknown>) {
    setBusy(key);
    try {
      await fn();
    } catch {
      /* surfaced via connection status */
    } finally {
      setBusy(null);
    }
  }

  const relayOn = Boolean(actuators.relay);
  const ac = simulated.ac ?? "off";
  const socket = simulated.socket ?? "off";
  const blinds = simulated.blinds ?? 0;

  return (
    <div className="panel">
      <h2>Manual Controls</h2>
      <div className="controls">
        <div className="control-group">
          <div className="title">
            <span>💡 LED Brightness</span>
            <span>{brightness}</span>
          </div>
          <input
            type="range"
            min={0}
            max={255}
            value={brightness}
            onChange={(e) => setBrightness(Number(e.target.value))}
            onMouseUp={() => run("led", () => sendLed(brightness))}
            onTouchEnd={() => run("led", () => sendLed(brightness))}
          />
        </div>

        <div className="control-group">
          <div className="title">
            <span>🌀 Relay (Fan / Heater)</span>
          </div>
          <div className="btn-group">
            <button
              className={`btn ${relayOn ? "active" : ""}`}
              disabled={busy === "relay-on"}
              onClick={() => run("relay-on", () => sendRelay("on"))}
            >
              On
            </button>
            <button
              className={`btn ${!relayOn ? "active" : ""}`}
              disabled={busy === "relay-off"}
              onClick={() => run("relay-off", () => sendRelay("off"))}
            >
              Off
            </button>
          </div>
        </div>

        <div className="control-group">
          <div className="title">
            <span>❄️ AC Unit</span>
          </div>
          <div className="btn-group">
            <button
              className={`btn ${ac === "cooling" ? "active" : ""}`}
              onClick={() => run("ac-cool", () => sendSimulated("ac", { state: "cooling" }))}
            >
              Cooling
            </button>
            <button
              className={`btn ${ac === "idle" ? "active" : ""}`}
              onClick={() => run("ac-idle", () => sendSimulated("ac", { state: "idle" }))}
            >
              Idle
            </button>
            <button
              className={`btn ${ac === "off" ? "active" : ""}`}
              onClick={() => run("ac-off", () => sendSimulated("ac", { state: "off" }))}
            >
              Off
            </button>
          </div>
        </div>

        <div className="control-group">
          <div className="title">
            <span>🪟 Blinds</span>
            <span>{blinds}%</span>
          </div>
          <div className="btn-group">
            <button
              className="btn"
              onClick={() => run("blinds-open", () => sendSimulated("blinds", { position: 100 }))}
            >
              Open
            </button>
            <button
              className="btn"
              onClick={() => run("blinds-half", () => sendSimulated("blinds", { position: 50 }))}
            >
              Half
            </button>
            <button
              className="btn"
              onClick={() => run("blinds-close", () => sendSimulated("blinds", { position: 0 }))}
            >
              Close
            </button>
          </div>
        </div>

        <div className="control-group">
          <div className="title">
            <span>🔌 Smart Socket</span>
          </div>
          <div className="btn-group">
            <button
              className={`btn ${socket === "on" ? "active" : ""}`}
              onClick={() => run("socket-on", () => sendSimulated("socket", { state: "on" }))}
            >
              On
            </button>
            <button
              className={`btn ${socket === "off" ? "active" : ""}`}
              onClick={() => run("socket-off", () => sendSimulated("socket", { state: "off" }))}
            >
              Off
            </button>
          </div>
        </div>

        <div className="control-group">
          <div className="title">
            <span>♻️ Replanning</span>
          </div>
          <div className="btn-group">
            <button
              className="btn danger"
              disabled={busy === "override"}
              onClick={() => run("override", () => sendManualOverride("dashboard"))}
            >
              Trigger Manual Replan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
