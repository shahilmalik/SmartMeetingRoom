import os
import time

from . import hardware

LIGHT_MAX = 1023.0
SOUND_MAX = 1023.0

# Occupancy is a deliberate "hand near the sensor" gesture, not a room sweep.
# Inside the demo box another device sits ~4 cm in front of the sensor, so the
# idle reading is a steady 4. Occupied therefore requires something CLOSER
# than that obstruction — a hand pressed right against the sensor:
#   - become OCCUPIED only when the distance drops to NEAR cm or less,
#   - become EMPTY again once it is back at FAR cm or more (the idle reading),
#   - hold the previous state in between (no flicker on a noisy reading).
# If the box is ever rearranged so the sensor has a clear view, relax these
# via OCCUPANCY_NEAR_CM / OCCUPANCY_FAR_CM in iot-node.service.
OCCUPANCY_NEAR_CM = float(os.environ.get("OCCUPANCY_NEAR_CM", "3"))
OCCUPANCY_FAR_CM = float(os.environ.get("OCCUPANCY_FAR_CM", "4"))
# Back-compat alias (some tooling still references this name).
OCCUPANCY_DISTANCE_CM = OCCUPANCY_NEAR_CM

_occ_state = {"occupied": False}


def _read_via_subprocess(call, default):
    # Real hardware reads share the serialized bus path with writes so a read
    # and an indicator write never bit-bang the software-I2C bus at once.
    return hardware.bus_call(call, default)


class CO2Model:
    def __init__(self, baseline=420.0):
        self.value = baseline
        self.baseline = baseline
        self._last = time.time()
        self._spike_until = 0.0

    def trigger_spike(self, amount=600.0, duration=15.0):
        self.value += amount
        self._spike_until = time.time() + duration

    def update(self, occupied, ventilating=False):
        now = time.time()
        dt = now - self._last
        self._last = now
        if occupied:
            self.value += 8.0 * dt
        else:
            self.value -= 5.0 * dt
        if now < self._spike_until:
            self.value += 4.0 * dt
        if ventilating:
            # Fresh-air fan clears CO2 quickly.
            self.value -= 20.0 * dt
        self.value = max(self.baseline, min(3000.0, self.value))
        return round(self.value, 1)


_co2 = CO2Model()


def read_temperature_humidity():
    if hardware.SIMULATION:
        result = hardware.read_dht(hardware.DHT_PORT)
        temp, hum = result[0], result[1]
        if temp is None or hum is None or temp != temp or hum != hum:
            return None, None
        return round(float(temp), 1), round(float(hum), 1)
    result = _read_via_subprocess("dht", [None, None])
    if not isinstance(result, (list, tuple)) or len(result) < 2:
        return None, None
    temp, hum = result[0], result[1]
    if temp is None or hum is None:
        return None, None
    try:
        return round(float(temp), 1), round(float(hum), 1)
    except (TypeError, ValueError):
        return None, None


def read_light():
    if hardware.SIMULATION:
        raw = hardware.read_analog(hardware.LIGHT_PORT)
        return raw, round((raw / LIGHT_MAX) * 100.0, 1)
    raw = _read_via_subprocess("analog0", 0)
    raw = raw if isinstance(raw, (int, float)) else 0
    return raw, round((raw / LIGHT_MAX) * 100.0, 1)


def read_noise():
    if hardware.SIMULATION:
        raw = hardware.read_analog(hardware.SOUND_PORT)
        return raw, round((raw / SOUND_MAX) * 100.0, 1)
    raw = _read_via_subprocess("analog1", 0)
    raw = raw if isinstance(raw, (int, float)) else 0
    return raw, round((raw / SOUND_MAX) * 100.0, 1)


def read_distance():
    if hardware.SIMULATION:
        return hardware.read_ultrasonic(hardware.ULTRASONIC_PORT)
    val = _read_via_subprocess("ultrasonic", None)
    return int(val) if isinstance(val, (int, float)) else None


def read_button():
    if hardware.SIMULATION:
        return int(hardware.read_digital(hardware.BUTTON_PORT))
    val = _read_via_subprocess("button", 0)
    return int(val) if isinstance(val, (int, float)) else 0


def read_occupancy():
    """Strict, debounced hand-detection. Returns (occupied, distance).
    A single bad/out-of-range reading never flips the state — it holds the
    previous value — so the demo stays stable despite ultrasonic jitter."""
    distance = read_distance()
    prev = _occ_state["occupied"]
    if distance is None or distance <= 0:
        # Sensor glitch / no echo — keep whatever we had.
        return prev, distance
    if distance <= OCCUPANCY_NEAR_CM:
        occupied = True
    elif distance >= OCCUPANCY_FAR_CM:
        occupied = False
    else:
        occupied = prev  # inside the hysteresis band → hold
    _occ_state["occupied"] = occupied
    return occupied, distance


def read_co2(occupied, ventilating=False):
    return _co2.update(occupied, ventilating=ventilating)


def spike_co2():
    _co2.trigger_spike()
