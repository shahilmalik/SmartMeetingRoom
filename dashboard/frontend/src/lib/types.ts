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
  actuators?: Actuators;
  breaches?: string[];
  health?: number;
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
}

export interface EventEntry {
  topic: string;
  payload: Record<string, unknown>;
  received: number;
}

export interface Overview {
  connected: boolean;
  sensors: Record<string, SensorReading>;
  state: RoomState;
  plan: Plan;
  simulated: Simulated;
  events: EventEntry[];
}
