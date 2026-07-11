"use client";

import { useCallback, useEffect, useState } from "react";
import { getOverview } from "@/lib/api";
import { Overview } from "@/lib/types";
import SensorCard from "@/components/SensorCard";
import HealthPanel from "@/components/HealthPanel";
import PlanView from "@/components/PlanView";
import EventLog from "@/components/EventLog";
import RoomVisual from "@/components/RoomVisual";
import Controls from "@/components/Controls";

const EMPTY: Overview = {
  connected: false,
  sensors: {},
  state: {},
  plan: {},
  simulated: {},
  events: [],
};

export default function Page() {
  const [data, setData] = useState<Overview>(EMPTY);
  const [online, setOnline] = useState<boolean>(false);

  const refresh = useCallback(async () => {
    try {
      const overview = await getOverview();
      setData(overview);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [refresh]);

  const { sensors, state, plan, simulated, events } = data;
  const actuators = state.actuators ?? {};

  return (
    <div className="container">
      <div className="topbar">
        <div className="brand">
          <div className="logo">🏢</div>
          <div>
            <h1>Smart Meeting Room</h1>
            <p>Live digital twin · AI planning · automated control</p>
          </div>
        </div>
        <div className="status-pill">
          <span className={`dot ${online && data.connected ? "on" : "off"}`} />
          {online ? (data.connected ? "Broker connected" : "API up · broker down") : "API offline"}
        </div>
      </div>

      <div className="grid cards">
        <SensorCard label="Temperature" icon="🌡️" reading={sensors.temperature} />
        <SensorCard label="Humidity" icon="💧" reading={sensors.humidity} max={100} />
        <SensorCard label="CO₂" icon="🫁" reading={sensors.co2} max={2000} />
        <SensorCard label="Noise" icon="🔊" reading={sensors.noise} max={100} />
        <SensorCard label="Light" icon="☀️" reading={sensors.light} max={100} />
        <SensorCard
          label="Occupancy"
          icon="🚶"
          reading={sensors.occupancy}
          fallback={state.occupied ? "Occupied" : "Empty"}
        />
      </div>

      <div className="section-title">Overview</div>
      <div className="grid main">
        <div className="grid" style={{ gap: 18 }}>
          <HealthPanel state={state} />
          <RoomVisual actuators={actuators} simulated={simulated} />
          <PlanView plan={plan} />
        </div>
        <div className="grid" style={{ gap: 18 }}>
          <Controls actuators={actuators} simulated={simulated} />
          <EventLog events={events} />
        </div>
      </div>
    </div>
  );
}
