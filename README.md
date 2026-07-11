# Smart Meeting Room

A smart meeting room that continuously monitors its environment (occupancy, temperature, humidity, CO2, noise, light) and uses an AI planner (Fast Downward / PDDL) to decide how to respond — adjusting ventilation, lighting, AC, blinds and device power. All modules are fully decoupled over an MQTT broker.

- **Occupied →** comfortable and healthy.
- **Empty →** energy-saving state.
- **Replanning triggers:** occupancy change, sensor threshold breach, periodic 60s tick, manual override from the dashboard.

## Architecture

```
            ┌─────────────┐   sensors/*        ┌─────────────────┐  state/current   ┌───────────────────┐
  Pi 5 ───▶ │  iot_node   │ ─────────────────▶ │  state_manager  │ ───────────────▶ │ problem_generator │
            └─────────────┘                    └─────────────────┘                  └───────────────────┘
                  ▲   actuators/*/cmd                  │ events/*                              │ planning/problem
                  │                                    ▼                                       ▼
            ┌─────────────┐  planning/plan      ┌─────────────┐  <── (replan triggers) ── ┌─────────┐
            │  executor   │ ◀────────────────── │             │                           │ planner │
            └─────────────┘                     └─────────────┘                           └─────────┘
                                                       ▲ Fast Downward subprocess + PDDL
                          state/* · plan · events      │
            ┌──────────────────────────┐               │
            │ dashboard (DRF + Next.js) │ ◀─────────────┘
            └──────────────────────────┘
```

Everything talks **only** through MQTT topics — no module calls another directly.

## Modules

| Module | Role |
| --- | --- |
| `iot_node/` | Runs on the Pi. Reads sensors, drives relay/LED, publishes `sensors/*`, subscribes `actuators/*/cmd`. |
| `shared/` | `mqtt_topics.py` — topic constants shared by all Python modules. |
| `state_manager/` | Digital twin. Subscribes `sensors/*`, maintains state, computes health score, publishes `state/current`, emits threshold/tick events. |
| `problem_generator/` | Turns state + goal into a PDDL problem, publishes `planning/problem`. |
| `planner/` | Runs Fast Downward as a subprocess on the PDDL domain+problem, publishes `planning/plan`. Falls back to a built-in solver if Fast Downward is not installed. |
| `executor/` | Consumes the plan, sends `actuators/*/cmd`, runs simulated AC/blinds/socket, publishes progress. |
| `dashboard/backend/` | Django + DRF API. Background MQTT thread mirrors live state; `@api_view` endpoints expose it and accept commands. |
| `dashboard/frontend/` | Next.js dashboard — live sensors, health score, room state, active plan, event log, manual controls. |

## Hardware (Pi 5 + GrovePi+)

| Module | Port | Type |
| --- | --- | --- |
| DHT11 temp/humidity | D4 | real |
| LED (dim/brighten, PWM) | D3 | real |
| Relay (fan/heater) | D5 | real |
| Ultrasonic ranger (occupancy) | D7 | real |
| Button (manual override) | D8 | real |
| Light sensor | A0 | real |
| Sound sensor | A1 | real |
| CO2 | — | simulated (software model) |
| AC unit | — | simulated state machine |
| Blinds | — | simulated position 0–100% |
| Smart socket | — | simulated on/off |

All Pi sensor/actuator access goes through the patched `grovepi.py` + `grove_sw_i2c.py` (software I2C via `lgpio`). The IoT node also runs with `IOT_SIMULATION=1` on any machine without the hardware.

## Running it

### 1. MQTT broker (Mosquitto)

```bash
docker compose up -d            # broker on localhost:1883 (+ websockets 9001)
```

Or with a local install: `mosquitto -p 1883`.

### 2. Python services (laptop)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MQTT_HOST=localhost
IOT_SIMULATION=1 ./run_services.sh      # state_manager, problem_generator, planner, executor, iot_node
```

On the Pi, only the IoT node runs (against the laptop's broker):

```bash
pip install -r iot_node/requirements.txt
MQTT_HOST=<laptop-ip> python3 -m iot_node.main
```

A `iot_node/iot-node.service` systemd unit is included.

### 3. Dashboard backend (Django + DRF)

```bash
cd dashboard/backend
pip install -r requirements.txt
MQTT_HOST=localhost python manage.py runserver 0.0.0.0:8000
```

### 4. Dashboard frontend (Next.js)

```bash
cd dashboard/frontend
npm install
npm run dev                     # http://localhost:3000
```

## AI Planner (Fast Downward)

The planner invokes `fast-downward.py --alias lama-first`. Set `FAST_DOWNWARD` to its path if it is not on `PATH`. The PDDL domain is `planner/domain.pddl`. If Fast Downward is not available, the planner uses an equivalent built-in resolver so the demo still runs.

## REST API

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health/` | API + broker status |
| GET | `/api/overview/` | full snapshot (sensors, state, plan, simulated, events) |
| GET | `/api/sensors/` | latest sensor readings |
| GET | `/api/state/` | current digital-twin state |
| GET | `/api/plan/` | active plan |
| GET | `/api/events/` | recent events |
| POST | `/api/commands/relay/` | `{ "state": "on" \| "off" }` |
| POST | `/api/commands/led/` | `{ "brightness": 0-255 }` |
| POST | `/api/commands/simulated/` | `{ "actuator": "ac\|blinds\|socket", ... }` |
| POST | `/api/commands/manual-override/` | trigger a manual replan |

## MQTT Topic Map

- `sensors/{id}` — readings from the Pi (temperature, humidity, light, noise, occupancy, co2)
- `actuators/{id}/cmd` — commands to the Pi / executor (relay, led, ac, blinds, socket)
- `state/current` — digital twin state
- `state/actuators`, `state/simulated` — actuator snapshots
- `planning/problem`, `planning/plan` — PDDL problem instances and plans
- `events/*` — replan triggers (occupancy, threshold, tick, manual) and execution progress

## Environment variables

| Variable | Default | Used by |
| --- | --- | --- |
| `MQTT_HOST` | `localhost` | all |
| `MQTT_PORT` | `1883` | all |
| `IOT_SIMULATION` | `0` | iot_node (`1` = no hardware) |
| `IOT_INTERVAL` | `2.0` | iot_node poll seconds |
| `STATE_TICK` | `60.0` | state_manager periodic replan |
| `FAST_DOWNWARD` | `fast-downward.py` | planner |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000/api` | frontend |
