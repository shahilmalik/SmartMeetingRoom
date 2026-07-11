"use client";

import { Actuators, Simulated } from "@/lib/types";

interface Props {
  actuators: Actuators;
  simulated: Simulated;
}

export default function RoomVisual({ actuators, simulated }: Props) {
  const led = actuators.led ?? 0;
  const relay = actuators.relay ?? 0;
  const ac = simulated.ac ?? "off";
  const blinds = simulated.blinds ?? 0;
  const socket = simulated.socket ?? "off";

  const tiles = [
    {
      glyph: "💡",
      name: "LED Lights",
      st: led > 0 ? `${Math.round((led / 255) * 100)}%` : "Off",
      on: led > 0,
    },
    {
      glyph: "🌀",
      name: "Relay (Fan/Heater)",
      st: relay ? "On" : "Off",
      on: Boolean(relay),
    },
    {
      glyph: "❄️",
      name: "AC Unit",
      st: ac.charAt(0).toUpperCase() + ac.slice(1),
      on: ac === "cooling",
    },
    {
      glyph: "🪟",
      name: "Blinds",
      st: `${blinds}% open`,
      on: blinds > 0,
    },
    {
      glyph: "🔌",
      name: "Smart Socket",
      st: socket === "on" ? "Powered" : "Off",
      on: socket === "on",
    },
  ];

  return (
    <div className="panel">
      <h2>Room & Actuators</h2>
      <div className="room">
        {tiles.map((tile) => (
          <div className="tile" key={tile.name}>
            <div className="glyph" style={{ opacity: tile.on ? 1 : 0.4 }}>
              {tile.glyph}
            </div>
            <div className="name">{tile.name}</div>
            <div className="st" style={{ color: tile.on ? "var(--good)" : "var(--muted)" }}>
              {tile.st}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
