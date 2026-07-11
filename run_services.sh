#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"
export IOT_SIMULATION="${IOT_SIMULATION:-1}"

PIDS=()

cleanup() {
  echo "Stopping services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

start() {
  echo "Starting $1"
  python3 -m "$1" &
  PIDS+=($!)
}

start state_manager.main
start problem_generator.main
start planner.main
start executor.main

echo "All laptop services started (PID: ${PIDS[*]}). Press Ctrl+C to stop."
wait
