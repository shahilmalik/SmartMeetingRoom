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
import ActuatorShowcase from "@/components/ActuatorShowcase";
import Banner from "@/components/Banner";
import SensorOverridePanel from "@/components/SensorOverridePanel";
import ActuatorTestDrawer from "@/components/ActuatorTestDrawer";

const EMPTY: Overview = {
  connected: false,
  pi_online: false,
  pi_last_seen: null,
  sensors: {},
  state: {},
  plan: {},
  simulated: {},
  overrides: {},
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

  const { sensors, state, plan, simulated, overrides, events } = data;
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
        <div style={{ display: "flex", gap: 10 }}>
          <div className="status-pill">
            <span className={`dot ${online && data.connected ? "on" : "off"}`} />
            {online ? (data.connected ? "Broker connected" : "API up · broker down") : "API offline"}
          </div>
          <div
            className="status-pill"
            title={
              data.pi_last_seen
                ? `Last sensor data: ${new Date(data.pi_last_seen * 1000).toLocaleTimeString()}`
                : "No sensor data received yet"
            }
          >
            <span className={`dot ${online && data.pi_online ? "on" : "off"}`} />
            {online && data.pi_online ? "🍓 Pi live" : "Pi offline"}
          </div>
        </div>
      </div>

      <Banner state={state} />

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

      <div className="section-title">Automated Actuators</div>
      <ActuatorShowcase simulated={simulated} />

      <div className="section-title">Overview</div>
      <div className="grid main">
        <div className="grid" style={{ gap: 18 }}>
          <HealthPanel state={state} />
          <RoomVisual actuators={actuators} simulated={simulated} />
          <PlanView plan={plan} />
        </div>
        <div className="grid" style={{ gap: 18 }}>
          <SensorOverridePanel
            sensors={sensors}
            overrides={overrides}
            daylight={state.daylight}
            occupied={state.occupied}
          />
          <Controls actuators={actuators} simulated={simulated} />
          <EventLog events={events} />
        </div>
      </div>

      <ActuatorTestDrawer actuators={actuators} simulated={simulated} />
    </div>
  );
}
