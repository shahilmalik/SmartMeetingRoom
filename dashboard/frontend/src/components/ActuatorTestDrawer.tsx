"use client";

import { useState } from "react";
import { Actuators, Simulated } from "@/lib/types";
import { sendSimulated, testActuator } from "@/lib/api";

interface Props {
  actuators: Actuators;
  simulated: Simulated;
}

export default function ActuatorTestDrawer({ actuators, simulated }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<unknown>) {
    setBusy(key);
    try {
      await fn();
    } catch {
      /* surfaced via connection status */
    } finally {
      // keep the button "armed" for the pulse duration so it reads as active
      setTimeout(() => setBusy((b) => (b === key ? null : b)), 400);
    }
  }

  const buzzerOn = Boolean(actuators.buzzer);
  const ledOn = (actuators.led ?? 0) > 0;
  const lampOn = (simulated.socket ?? "off") === "on";

  return (
    <div className={`test-drawer ${open ? "open" : ""}`}>
      <button
        className="test-tab"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close actuator tests" : "Open actuator tests"}
      >
        <span className="test-arrow">{open ? "▶" : "◀"}</span>
        <span className="test-tab-label">TEST</span>
      </button>

      <div className="test-body">
        <h3>Hardware Test</h3>
        <p className="test-sub">
          Fire each physical actuator directly — bypasses the noise / health
          logic so you can confirm the wiring.
        </p>

        <div className="test-item">
          <span className={`test-dot ${buzzerOn ? "on" : ""}`} />
          <div className="test-meta">
            <div className="test-name">🔔 Health Buzzer</div>
            <div className="test-state">{buzzerOn ? "Sounding" : "Silent"}</div>
          </div>
          <button
            className="btn small"
            disabled={busy === "buzzer"}
            onClick={() => run("buzzer", () => testActuator("buzzer", 2))}
          >
            Beep 2s
          </button>
        </div>

        <div className="test-item">
          <span className={`test-dot ${ledOn ? "on" : ""}`} />
          <div className="test-meta">
            <div className="test-name">🔆 Noise LED</div>
            <div className="test-state">{ledOn ? "Blinking" : "Off"}</div>
          </div>
          <button
            className="btn small"
            disabled={busy === "led"}
            onClick={() => run("led", () => testActuator("led", 3))}
          >
            Blink 3s
          </button>
        </div>

        <div className="test-item">
          <span className={`test-dot ${lampOn ? "on" : ""}`} />
          <div className="test-meta">
            <div className="test-name">💡 Room Light</div>
            <div className="test-state">{lampOn ? "On" : "Off"}</div>
          </div>
          <div className="btn-group">
            <button
              className={`btn small ${lampOn ? "active" : ""}`}
              disabled={busy === "lamp-on"}
              onClick={() => run("lamp-on", () => sendSimulated("socket", { state: "on" }))}
            >
              On
            </button>
            <button
              className={`btn small ${!lampOn ? "active" : ""}`}
              disabled={busy === "lamp-off"}
              onClick={() => run("lamp-off", () => sendSimulated("socket", { state: "off" }))}
            >
              Off
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
