import json
import os
import subprocess
import sys
import time

from . import hardware

OCCUPANCY_DISTANCE_CM = 50
LIGHT_MAX = 1023.0
SOUND_MAX = 1023.0
READ_TIMEOUT = int(os.environ.get("SENSOR_TIMEOUT", "5"))

_READER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_reader.py")


def _read_via_subprocess(call, default):
    if hardware.SIMULATION:
        try:
            return eval(call, {"__builtins__": {}}, _sim_ctx())
        except Exception:
            return default
    try:
        result = subprocess.run(
            [sys.executable, _READER_SCRIPT, call],
            capture_output=True, text=True, timeout=READ_TIMEOUT,
            env={**os.environ, "PYTHONPATH": ":".join([
                "/home/shahilmalik",
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ])}
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        if result.stderr.strip():
            print(f"[sensors] {call}: {result.stderr.strip()}", file=sys.stderr, flush=True)
        return default
    except subprocess.TimeoutExpired:
        print(f"[sensors] TIMEOUT({READ_TIMEOUT}s): {call} - bus may be wedged", file=sys.stderr, flush=True)
        return default
    except Exception as e:
        print(f"[sensors] ERROR {call}: {e}", file=sys.stderr, flush=True)
        return default


def _sim_ctx():
    from . import hardware as hw
    return {"hw": hw}


class CO2Model:
    def __init__(self, baseline=420.0):
        self.value = baseline
        self.baseline = baseline
        self._last = time.time()
        self._spike_until = 0.0

    def trigger_spike(self, amount=600.0, duration=15.0):
        self.value += amount
        self._spike_until = time.time() + duration

    def update(self, occupied):
        now = time.time()
        dt = now - self._last
        self._last = now
        if occupied:
            self.value += 8.0 * dt
        else:
            self.value -= 5.0 * dt
        if now < self._spike_until:
            self.value += 4.0 * dt
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
    distance = read_distance()
    occupied = distance is not None and distance <= OCCUPANCY_DISTANCE_CM
    return occupied, distance


def read_co2(occupied):
    return _co2.update(occupied)


def spike_co2():
    _co2.trigger_spike()
