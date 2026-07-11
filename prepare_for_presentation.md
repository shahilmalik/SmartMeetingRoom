# Presentation Preparation — Smart Meeting Room

This document maps every topic from the practical slides to how it is implemented in this project.

---

## Slide 01 — Overview & Logistics: What we built

The project is a **Smart Meeting Room** that continuously monitors its environment and autonomously adapts it using an AI planner.

Two operating modes:
- **Occupied** → achieve comfort (temperature, air quality, lighting, device power)
- **Empty** → achieve energy-saving (everything off/closed)

All components were implemented and are running end-to-end.

---

## Slide 02 — Systems Design

### Required: Decoupled, service-based architecture

We built 7 fully decoupled services that talk only through MQTT — no direct calls between modules:

```
iot_node  →  state_manager  →  problem_generator  →  planner  →  executor
                                                              ↓
                                                        dashboard (DRF + Next.js)
```

| Module | File | Role |
|---|---|---|
| `iot_node` | `iot_node/main.py` | Reads sensors, drives actuators on the Pi |
| `state_manager` | `state_manager/main.py` | Digital twin — aggregates sensor data, computes health score, emits events |
| `problem_generator` | `problem_generator/main.py` | Translates current state + goal into a PDDL problem |
| `planner` | `planner/main.py` | Runs Fast Downward, publishes the action plan |
| `executor` | `executor/main.py` | Executes the plan step-by-step, drives actuators |
| `dashboard/backend` | `dashboard/backend/` | Django + DRF REST API, mirrors live MQTT state |
| `dashboard/frontend` | `dashboard/frontend/` | Next.js live dashboard with manual controls |

Each service is independently runnable. Entry point: `run_services.sh`.

---

## Slide 03 — IoT

### Required: Real sensors and actuators on hardware

We run on a **Raspberry Pi 5 + GrovePi+** with the following hardware:

| Sensor / Actuator | Grove Port | Type |
|---|---|---|
| DHT11 (temperature + humidity) | D4 | Real |
| LED (PWM brightness control) | D3 | Real |
| Relay (fan / heater) | D5 | Real |
| Ultrasonic ranger (occupancy detection) | D7 | Real |
| Button (manual override) | D8 | Real |
| Light sensor | A0 | Real |
| Sound sensor | A1 | Real |
| CO2 | — | Software model (`sensors.py:50-72`) |
| AC unit | — | Simulated state machine (`executor/main.py:14-34`) |
| Blinds | — | Simulated position 0–100% |
| Smart socket | — | Simulated on/off |

**Sensors** (`iot_node/sensors.py`):
- Temperature/humidity via DHT11 on D4
- Occupancy via ultrasonic ranger (threshold: ≤50 cm = occupied)
- Light and noise from analog ports A0/A1, normalized to 0–100%
- CO2 modelled as a time-evolving value: rises at +8 ppm/s when occupied, decays at −5 ppm/s when empty

**Simulation mode**: `IOT_SIMULATION=1` runs the full pipeline on any laptop without hardware.

**Sensor publishing**: every 2 seconds (configurable via `IOT_INTERVAL`), readings are published as retained MQTT messages to `sensors/{id}` with timestamp and unit metadata.

---

## Slide 04 — Indirect Communication (MQTT)

### Required: Publish/subscribe messaging over MQTT

We use **Eclipse Mosquitto** as the broker, running in Docker:

```bash
docker compose up -d   # broker on :1883 (TCP) + :9001 (WebSocket)
```

All topic constants are centralised in `shared/mqtt_topics.py` — no magic strings in any module.

**Topic map:**

| Topic | Direction | Purpose |
|---|---|---|
| `sensors/{id}` | Pi → all | Live sensor readings (retained) |
| `actuators/{id}/cmd` | executor → Pi | Actuator commands |
| `state/current` | state_manager → all | Full digital-twin snapshot (retained) |
| `state/actuators` | Pi → state_manager | Actuator feedback |
| `state/simulated` | executor → all | AC / blinds / socket state (retained) |
| `planning/problem` | problem_generator → planner | PDDL problem instance |
| `planning/plan` | planner → executor | Resolved action plan (retained) |
| `events/occupancy` | state_manager → all | Occupancy change trigger |
| `events/threshold` | state_manager → all | Sensor breach trigger |
| `events/tick` | state_manager → all | Periodic 60s replan trigger |
| `events/manual` | iot_node / dashboard → all | Manual override trigger |
| `events/executed` | executor → all | Step-by-step execution progress |
| `events/plan_done` | executor → all | Plan completion notification |

**Replan triggers** (`problem_generator/main.py:26-41`): a new PDDL problem is generated on occupancy change, sensor threshold breach, 60-second tick, or manual override — always from the latest retained state.

---

## Slide 05 — AI Planning

### Required: Use an AI planner to decide actions

The `planner/` module implements the full AI planning loop:

1. Subscribes to `planning/problem`
2. Calls **Fast Downward** as a subprocess with the PDDL domain + problem
3. Parses the output plan file
4. Publishes the resulting action sequence to `planning/plan`

**Why AI planning and not rules?** The planner finds the shortest valid action sequence to reach the goal given the current state, respecting all preconditions. Adding a new actuator or constraint only requires updating the PDDL domain — no rule logic to rewrite.

**Fallback** (`planner/main.py:101-138`): if Fast Downward is not installed, a built-in rule-based fallback (`fallback_solve`) produces equivalent plans so the demo always works.

**Goal selection** (`problem_generator/main.py:81-84`):
- Room occupied → goal: `(comfortable room1)`
- Room empty → goal: `(energy-saving room1)`

---

## Slide 06 — PDDL

### Required: Model the domain and problem in PDDL

**Domain file:** `planner/domain.pddl`

Requirements used: `:strips :typing :negative-preconditions`

**Predicates** (room state facts):
- Occupancy: `occupied`, `empty`
- Temperature: `temp-comfortable`, `temp-hot`, `temp-cold`
- Air quality: `co2-high`, `co2-ok`
- Lighting: `lights-on`, `lights-off`, `lights-dim`, `lights-bright`
- Ventilation: `ventilation-on`, `ventilation-off`
- Cooling: `ac-cooling`, `ac-off`
- Blinds: `blinds-open`, `blinds-closed`
- Device: `device-powered`, `device-off`
- Goal states: `comfortable`, `energy-saving`

**Actions (13 total):**

| Action | Preconditions | Effects |
|---|---|---|
| `ventilate` | `co2-high`, `ventilation-off` | ventilation on, CO2 ok |
| `stop-ventilation` | `ventilation-on`, `co2-ok`, `empty` | ventilation off |
| `cool-room` | `temp-hot`, `ac-off`, `occupied` | AC cooling, temp comfortable |
| `stop-cooling` | `ac-cooling`, `temp-comfortable` | AC off |
| `heat-room` | `temp-cold`, `ventilation-off`, `occupied` | ventilation on, temp comfortable |
| `brighten-lights` | `occupied`, `lights-dim` | lights bright |
| `dim-lights` | `occupied`, `lights-bright` | lights dim |
| `turn-off-lights` | `empty`, `lights-on` | lights off |
| `open-blinds` | `occupied`, `blinds-closed` | blinds open |
| `close-blinds` | `empty`, `blinds-open` | blinds closed |
| `power-up-device` | `occupied`, `device-off` | device powered |
| `power-down-device` | `empty`, `device-powered` | device off |
| `achieve-comfort` | `occupied`, temp ok, co2 ok, lights bright, device powered | `comfortable` |
| `achieve-energy-saving` | `empty`, lights off, ventilation off, AC off, device off, blinds closed | `energy-saving` |

**Problem generation** (`problem_generator/main.py:52-104`): the `ProblemGenerator` reads the current digital-twin state and renders a valid PDDL problem at runtime — mapping sensor values (temperature range, CO2 threshold, LED brightness, relay state, occupancy) to PDDL predicates.

Example generated problem:
```pddl
(define (problem meeting-room-state)
  (:domain smart-meeting-room)
  (:objects room1 - room)
  (:init
    (occupied room1)
    (temp-hot room1)
    (co2-high room1)
    (lights-dim room1)
    (lights-on room1)
    (ventilation-off room1)
    (ac-off room1)
    (blinds-open room1)
    (device-powered room1)
  )
  (:goal (and
    (comfortable room1)
  ))
)
```

---

## Slide 07 — AI Planning Tools

### Required: Use Fast Downward as the planning engine

**Planner:** [Fast Downward](https://www.fast-downward.org/)
**Search alias:** `lama-first` (LAMA — Landmark-Aware heuristic search, anytime mode)

Invocation (`planner/main.py:65-73`):
```bash
fast-downward.py --alias lama-first --plan-file plan.out domain.pddl problem.pddl
```

- Runs in a temporary working directory per planning call
- 30-second timeout per call
- Plan file is parsed line-by-line to extract the action sequence
- Configurable via `FAST_DOWNWARD` and `FD_ALIAS` environment variables

**Action-to-actuator mapping** (`planner/main.py:17-30`): each PDDL action name maps to a concrete actuator command (e.g. `cool-room` → `{"actuator": "ac", "state": "cooling"}`), which the executor then dispatches.

---

## Slide 08 — Context / Dashboard

### Required: Visualise state and allow manual interaction

**REST API** (Django + DRF, `dashboard/backend/`):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/overview/` | GET | Full snapshot: sensors, state, plan, simulated actuators, events |
| `/api/sensors/` | GET | Latest sensor readings |
| `/api/state/` | GET | Current digital-twin state + health score |
| `/api/plan/` | GET | Active plan from planner |
| `/api/events/` | GET | Recent event log |
| `/api/commands/relay/` | POST | Control fan/heater relay |
| `/api/commands/led/` | POST | Control LED brightness (0–255) |
| `/api/commands/simulated/` | POST | Control simulated AC, blinds, socket |
| `/api/commands/manual-override/` | POST | Trigger immediate replan |

**Frontend** (Next.js, `dashboard/frontend/`):
- Live sensor readings (temperature, humidity, light, noise, CO2)
- Health score (0–100, computed from active breaches)
- Current room state (occupied/empty, comfortable/not)
- Active plan with step-by-step action list
- Simulated actuator states (AC, blinds, socket)
- Event log (occupancy, threshold, tick, manual, executed, plan_done)
- Manual controls for all actuators + manual replan button

**Health score** (`state_manager/main.py:78-94`): computed by deducting from 100 for each active breach — −20 for temperature, −10 for humidity, −25 for CO2 warn, −15 additional for CO2 critical, −10 for noise, −10 for extreme temperature.

---

## Summary — What was asked vs. what we delivered

| Practical slide topic | Delivered |
|---|---|
| System design with decoupled services | 7 independent modules, all connected only via MQTT |
| IoT node with real sensors on hardware | Pi 5 + GrovePi+, 5 real sensors + 2 real actuators, simulation mode |
| Indirect communication via MQTT broker | Eclipse Mosquitto in Docker, 15 topic channels, all constants centralised |
| AI Planning as decision engine | Fast Downward (`lama-first`) running as subprocess per replan cycle |
| PDDL domain modelling | `domain.pddl` with 13 actions, 20 predicates, STRIPS + typing |
| PDDL problem generation from live state | `problem_generator` builds and publishes a PDDL problem on every trigger |
| AI Planning Tools (Fast Downward) | Invoked with `--alias lama-first`, fallback solver included |
| Dashboard / context visualisation | Next.js frontend + DRF REST API, live state, manual override |
