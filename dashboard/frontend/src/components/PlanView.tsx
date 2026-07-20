"use client";

import { Plan } from "@/lib/types";

const ACTION_ICONS: Record<string, string> = {
  ventilate: "🌬️",
  "stop-ventilation": "🛑",
  "cool-room": "❄️",
  "stop-cooling": "🌡️",
  "heat-room": "🔥",
  "open-blinds-for-daylight": "🪟",
  "close-blinds-for-cooling": "🧱",
  "close-blinds": "🧱",
  "turn-on-lamp-night": "💡",
  "turn-on-lamp-hot": "💡",
  "turn-off-lamp": "🌑",
  "achieve-comfort": "✅",
  "achieve-energy-saving": "🍃",
};

const ACTION_LABELS: Record<string, string> = {
  "open-blinds-for-daylight": "Open Blinds · daylight",
  "close-blinds-for-cooling": "Close Blinds · block heat",
  "turn-on-lamp-night": "Room Lamp On · night",
  "turn-on-lamp-hot": "Room Lamp On · blinds shut",
  "turn-off-lamp": "Room Lamp Off",
  ventilate: "Ventilate · clear CO₂",
  "heat-room": "Heat Room",
};

function describe(action: string): string {
  if (ACTION_LABELS[action]) return ACTION_LABELS[action];
  return action.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function PlanView({ plan }: { plan: Plan }) {
  const steps = plan.steps ?? [];

  return (
    <div className="panel">
      <h2>Active Plan</h2>
      {plan.goal ? (
        <div className="row">
          <span className="k">Goal</span>
          <span className="v">
            <span className="tag good">{plan.goal}</span>
          </span>
        </div>
      ) : null}
      {plan.trigger ? (
        <div className="row">
          <span className="k">Triggered by</span>
          <span className="v">{plan.trigger.replace("events/", "")}</span>
        </div>
      ) : null}

      <div style={{ marginTop: 14 }}>
        {steps.length === 0 ? (
          <div className="empty">No plan yet. Waiting for the planner…</div>
        ) : (
          steps.map((step, index) => (
            <div className="plan-step" key={`${step.action}-${index}`}>
              <span className="num">{index + 1}</span>
              <span>{ACTION_ICONS[step.action] ?? "⚙️"}</span>
              <span>{describe(step.action)}</span>
              {step.actuator ? <span className="meta">{step.actuator}</span> : null}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
