"use client";

import { useState } from "react";
import { Actuators, Simulated } from "@/lib/types";
import { sendManualOverride, sendRelay, sendSimulated } from "@/lib/api";

interface Props {
  actuators: Actuators;
  simulated: Simulated;
}

export default function Controls({ actuators, simulated }: Props) {
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
  const socket = simulated.socket ?? "off";
  const socketMode = simulated.socket_mode ?? "auto";

  return (
    <div className="panel">
      <h2>Manual Controls</h2>
      <div className="controls">
        <div className="control-group">
          <div className="title">
            <span>🌀 Fan / Heater</span>
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
            <span>💡 Room Light (Plugwise)</span>
            <span
              className={`tag ${socketMode === "manual" ? "warn" : "good"}`}
              title={
                socketMode === "manual"
                  ? "A human holds the lamp — the planner won't touch it until Auto"
                  : "The AI planner controls the lamp"
              }
            >
              {socketMode === "manual" ? "✋ Manual" : "🤖 Auto"}
            </span>
          </div>
          <div className="btn-group">
            <button
              className={`btn ${socket === "on" ? "active" : ""}`}
              disabled={busy === "socket-on"}
              onClick={() => run("socket-on", () => sendSimulated("socket", { state: "on" }))}
            >
              On
            </button>
            <button
              className={`btn ${socket === "off" ? "active" : ""}`}
              disabled={busy === "socket-off"}
              onClick={() => run("socket-off", () => sendSimulated("socket", { state: "off" }))}
            >
              Off
            </button>
            <button
              className="btn"
              disabled={busy === "socket-auto"}
              onClick={() => run("socket-auto", () => sendSimulated("socket", { state: "auto" }))}
            >
              Auto
            </button>
          </div>
          <span className="hint">
            On/Off hold the lamp manually (planner won’t override). Auto hands
            control back to the AI planner.
          </span>
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
