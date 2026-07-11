"use client";

import { EventEntry } from "@/lib/types";

function relativeTime(ts: number): string {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function summarize(entry: EventEntry): string {
  const payload = entry.payload || {};
  if ("breaches" in payload) {
    return `Breach: ${(payload.breaches as string[]).join(", ")}`;
  }
  if ("occupied" in payload) {
    return payload.occupied ? "Room became occupied" : "Room became empty";
  }
  if ("source" in payload) {
    return `Manual override (${payload.source})`;
  }
  if ("executed" in payload) {
    return `Executed: ${payload.executed}`;
  }
  if ("length" in payload) {
    return `Plan complete (${payload.length} steps)`;
  }
  return "Periodic re-evaluation";
}

export default function EventLog({ events }: { events: EventEntry[] }) {
  return (
    <div className="panel">
      <h2>Event Log</h2>
      {events.length === 0 ? (
        <div className="empty">No events recorded yet.</div>
      ) : (
        events.map((entry, index) => (
          <div className="event" key={`${entry.topic}-${entry.received}-${index}`}>
            <span className="when">{relativeTime(entry.received)}</span>
            <div>
              <div className="topic">{entry.topic.replace("events/", "")}</div>
              <div style={{ color: "var(--muted)" }}>{summarize(entry)}</div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
