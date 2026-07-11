import { Overview } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getOverview(): Promise<Overview> {
  return request<Overview>("/overview/");
}

export function sendRelay(state: "on" | "off") {
  return request("/commands/relay/", {
    method: "POST",
    body: JSON.stringify({ state }),
  });
}

export function sendLed(brightness: number) {
  return request("/commands/led/", {
    method: "POST",
    body: JSON.stringify({ brightness }),
  });
}

export function sendSimulated(
  actuator: "ac" | "blinds" | "socket",
  payload: { state?: string; position?: number }
) {
  return request("/commands/simulated/", {
    method: "POST",
    body: JSON.stringify({ actuator, ...payload }),
  });
}

export function sendManualOverride(reason: string) {
  return request("/commands/manual-override/", {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
