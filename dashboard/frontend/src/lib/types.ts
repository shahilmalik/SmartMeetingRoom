export interface SensorReading {
  id: string;
  value: number;
  ts: number;
  unit?: string;
  raw?: number;
  distance_cm?: number;
  occupied?: boolean;
}

export interface Actuators {
  relay?: number;
  led?: number;
  buzzer?: number;
}

export interface HealthFactor {
  label: string;
  delta: number;
  ok: boolean;
  detail: string;
}

export interface RoomState {
  ts?: number;
  occupied?: boolean;
  occupancy_distance_cm?: number | null;
  temperature?: number | null;
  humidity?: number | null;
  light?: number | null;
  noise?: number | null;
  co2?: number | null;
  daylight?: boolean;
  actuators?: Actuators;
  breaches?: string[];
  health?: number;
  health_factors?: HealthFactor[];
  noise_high?: boolean;
  comfortable?: boolean;
  light_status?: string;
}

export interface PlanStep {
  action: string;
  actuator?: string;
  state?: string;
  brightness?: number;
  position?: number;
}

export interface Plan {
  ts?: number;
  trigger?: string;
  goal?: string;
  actions?: string[];
  steps?: PlanStep[];
  length?: number;
}

export interface Simulated {
  ts?: number;
  ac?: string;
  blinds?: number;
  socket?: string;
  socket_mode?: "manual" | "auto";
}

export interface EventEntry {
  topic: string;
  payload: Record<string, unknown>;
  received: number;
}

export type SensorOverrides = Record<string, number>;

export interface Overview {
  connected: boolean;
  pi_online?: boolean;
  pi_last_seen?: number | null;
  sensors: Record<string, SensorReading>;
  state: RoomState;
  plan: Plan;
  simulated: Simulated;
  overrides: SensorOverrides;
  events: EventEntry[];
}
