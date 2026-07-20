import json
import os
import random
import subprocess
import sys
import threading
import time

SIMULATION = os.environ.get("IOT_SIMULATION", "0") == "1"

# Every real-hardware bus operation (read AND write) runs in a fresh, short-lived
# subprocess (_reader.py). A fresh process re-initialises the patched software-I2C
# bus each time, which avoids the long-lived-process wedge; the lock guarantees
# only one such subprocess bit-bangs the bus at a time, so a read and a write can
# never collide and corrupt each other.
READ_TIMEOUT = int(os.environ.get("SENSOR_TIMEOUT", "5"))
_READER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_reader.py")
_GROVE_HOME = os.environ.get("GROVE_HOME", os.path.expanduser("~"))
_bus_lock = threading.Lock()

LIGHT_PORT = 0
SOUND_PORT = 1
LED_PORT = 3
DHT_PORT = 4
# D5 used to drive the Grove relay. There is no physical relay any more, so the
# freed D5 port now carries the buzzer (health alarm). Overridable via env.
BUZZER_PORT = int(os.environ.get("BUZZER_PORT", "5"))
ULTRASONIC_PORT = 7
BUTTON_PORT = 8

DHT_BLUE = 0

_grovepi = None

if not SIMULATION:
    _grove_home = os.path.expanduser("~")
    if _grove_home not in sys.path:
        sys.path.insert(0, _grove_home)
    try:
        import grovepi as _grovepi
    except Exception as _e:
        print(f"[hardware] grovepi import failed ({_e}), falling back to simulation", flush=True)
        _grovepi = None
        SIMULATION = True


class _Simulator:
    def __init__(self):
        self._occupied = False
        self._last_toggle = time.time()
        self._button = 0
        self._relay = 0        # logical fan/heater (causal model only)
        self._led = 0
        self._buzzer = 0
        self._temp = 22.0
        self._hum = 45.0
        # Simulated-actuator + environment state, fed from the executor so the
        # sensor readings respond causally (blinds open → brighter/warmer, AC
        # cooling → cooler, lamp on → brighter).
        self._blinds = 0        # 0..100 % open
        self._ac = "off"        # off | idle | cooling
        self._socket = "off"    # room lamp: on | off
        self._daylight = True   # is there daylight outside to harvest?

    def set_environment(self, blinds=None, ac=None, socket=None, daylight=None):
        if blinds is not None:
            self._blinds = int(blinds)
        if ac is not None:
            self._ac = ac
        if socket is not None:
            self._socket = socket
        if daylight is not None:
            self._daylight = bool(daylight)

    def _maybe_toggle_occupancy(self):
        now = time.time()
        if now - self._last_toggle > random.uniform(20, 45):
            self._occupied = not self._occupied
            self._last_toggle = now

    def analogRead(self, port):
        if port == LIGHT_PORT:
            # Light sources add up: natural daylight through the blinds +
            # the room lamp (socket) + a small LED contribution on the board.
            base = 30.0
            if self._daylight:
                base += (self._blinds / 100.0) * 560.0
            if self._socket == "on":
                base += 430.0
            base += (self._led / 255.0) * 120.0
            return int(max(0, min(1023, random.gauss(base, 8))))
        if port == SOUND_PORT:
            base = 480 if self._occupied else 180
            return int(max(0, min(1023, random.gauss(base, 15))))
        return 0

    def digitalRead(self, port):
        if port == BUTTON_PORT:
            if random.random() < 0.02:
                self._button = 1 - self._button
            return self._button
        return 0

    def digitalWrite(self, port, value):
        if port == BUZZER_PORT:
            self._buzzer = int(value)

    def analogWrite(self, port, value):
        if port == LED_PORT:
            self._led = int(value)

    def pinMode(self, port, mode):
        return None

    def dht(self, port, module_type):
        # Temperature drifts with the active thermal influences:
        #   AC cooling pulls it down, open blinds in daylight add solar gain,
        #   the relay (heater mode) pushes it up. This closes the loop so the
        #   planner's "close blinds → then cool" actually shows an effect.
        drift = random.uniform(-0.15, 0.15)
        if self._ac == "cooling":
            drift -= 0.45
        if self._daylight and self._blinds > 0:
            drift += 0.30 * (self._blinds / 100.0)
        if self._relay and self._temp < 22.0:
            drift += 0.35  # relay acting as heater
        self._temp = max(16.0, min(32.0, self._temp + drift))
        self._hum = max(25.0, min(75.0, self._hum + random.uniform(-0.8, 0.8)))
        return [round(self._temp, 1), round(self._hum, 1)]

    def ultrasonicRead(self, port):
        # Occupied = a "hand near the sensor" (short distance, within the strict
        # near threshold); empty = the far wall of the ~30 cm box.
        self._maybe_toggle_occupancy()
        if self._occupied:
            return int(max(3, random.gauss(8, 2)))
        return int(max(25, random.gauss(140, 25)))


_sim = _Simulator()


def bus_call(call, default=None):
    """Run one grovepi operation via a fresh, serialized subprocess and return
    its JSON result (or `default` on failure). Used for every real-hardware
    read and write so bus access is single-owner at any instant."""
    with _bus_lock:
        try:
            result = subprocess.run(
                [sys.executable, _READER_SCRIPT, call],
                capture_output=True, text=True, timeout=READ_TIMEOUT,
                env={**os.environ, "PYTHONPATH": ":".join([
                    _GROVE_HOME,
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ])},
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            if result.stderr.strip():
                print(f"[hardware] {call}: {result.stderr.strip()}", file=sys.stderr, flush=True)
            return default
        except subprocess.TimeoutExpired:
            print(f"[hardware] TIMEOUT({READ_TIMEOUT}s): {call} - bus may be wedged",
                  file=sys.stderr, flush=True)
            return default
        except Exception as e:
            print(f"[hardware] ERROR {call}: {e}", file=sys.stderr, flush=True)
            return default


def setup():
    if SIMULATION:
        return
    # pinMode runs in the same subprocess bus path as reads/writes.
    bus_call("setup", None)


def write_fan(on):
    """Logical fan/heater. No physical relay is wired, so on real hardware this
    is a no-op; in simulation it feeds the causal temperature/CO2 model."""
    if SIMULATION:
        _sim._relay = 1 if on else 0


def read_analog(port):
    if SIMULATION:
        return _sim.analogRead(port)
    return _grovepi.analogRead(port)


def read_digital(port):
    if SIMULATION:
        return _sim.digitalRead(port)
    return _grovepi.digitalRead(port)


def write_digital(port, value):
    if SIMULATION:
        _sim.digitalWrite(port, value)
        return
    bus_call(f"dwrite:{int(port)}:{int(value)}", None)


def write_analog(port, value):
    if SIMULATION:
        _sim.analogWrite(port, value)
        return
    bus_call(f"awrite:{int(port)}:{int(value)}", None)


def read_dht(port, module_type=DHT_BLUE):
    if SIMULATION:
        return _sim.dht(port, module_type)
    return _grovepi.dht(port, module_type)


def read_ultrasonic(port):
    if SIMULATION:
        return _sim.ultrasonicRead(port)
    return _grovepi.ultrasonicRead(port)


def set_sim_environment(blinds=None, ac=None, socket=None, daylight=None):
    """Feed simulated-actuator / daylight state into the sensor simulator so
    readings respond causally. No-op on real hardware."""
    if SIMULATION:
        _sim.set_environment(blinds=blinds, ac=ac, socket=socket, daylight=daylight)
