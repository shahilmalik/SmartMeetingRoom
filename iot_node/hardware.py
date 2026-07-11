import os
import random
import sys
import time

SIMULATION = os.environ.get("IOT_SIMULATION", "0") == "1"

LIGHT_PORT = 0
SOUND_PORT = 1
LED_PORT = 3
DHT_PORT = 4
RELAY_PORT = 5
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
        self._relay = 0
        self._led = 0
        self._temp = 22.0
        self._hum = 45.0

    def _maybe_toggle_occupancy(self):
        now = time.time()
        if now - self._last_toggle > random.uniform(20, 45):
            self._occupied = not self._occupied
            self._last_toggle = now

    def analogRead(self, port):
        if port == LIGHT_PORT:
            base = 600 if not self._occupied else 350
            return int(max(0, min(1023, random.gauss(base, 40))))
        if port == SOUND_PORT:
            base = 480 if self._occupied else 180
            return int(max(0, min(1023, random.gauss(base, 60))))
        return 0

    def digitalRead(self, port):
        if port == BUTTON_PORT:
            if random.random() < 0.02:
                self._button = 1 - self._button
            return self._button
        return 0

    def digitalWrite(self, port, value):
        if port == RELAY_PORT:
            self._relay = int(value)

    def analogWrite(self, port, value):
        if port == LED_PORT:
            self._led = int(value)

    def pinMode(self, port, mode):
        return None

    def dht(self, port, module_type):
        self._temp = max(16.0, min(32.0, self._temp + random.uniform(-0.3, 0.3)))
        self._hum = max(25.0, min(75.0, self._hum + random.uniform(-0.8, 0.8)))
        return [round(self._temp, 1), round(self._hum, 1)]

    def ultrasonicRead(self, port):
        self._maybe_toggle_occupancy()
        if self._occupied:
            return int(max(3, random.gauss(35, 8)))
        return int(max(60, random.gauss(140, 25)))


_sim = _Simulator()


def setup():
    if SIMULATION:
        return
    try:
        _grovepi.pinMode(LED_PORT, "OUTPUT")
        _grovepi.pinMode(RELAY_PORT, "OUTPUT")
        _grovepi.pinMode(BUTTON_PORT, "INPUT")
    except Exception:
        pass


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
    _grovepi.digitalWrite(port, value)


def write_analog(port, value):
    if SIMULATION:
        _sim.analogWrite(port, value)
        return
    _grovepi.analogWrite(port, value)


def read_dht(port, module_type=DHT_BLUE):
    if SIMULATION:
        return _sim.dht(port, module_type)
    return _grovepi.dht(port, module_type)


def read_ultrasonic(port):
    if SIMULATION:
        return _sim.ultrasonicRead(port)
    return _grovepi.ultrasonicRead(port)
