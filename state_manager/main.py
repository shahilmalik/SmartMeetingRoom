import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

TICK_INTERVAL = float(os.environ.get("STATE_TICK", "60.0"))

COMFORT_TEMP_MIN = 20.0
COMFORT_TEMP_MAX = 24.0
COMFORT_HUM_MIN = 30.0
COMFORT_HUM_MAX = 60.0
CO2_WARN = 1000.0
CO2_CRITICAL = 1400.0
NOISE_WARN = 65.0
LIGHT_LOW = 30.0
LIGHT_HIGH = 80.0
# Health at/below which the physical buzzer sounds (0-49 = "critical" band).
HEALTH_ALARM = float(os.environ.get("HEALTH_ALARM", "50"))


class StateManager:
    def __init__(self):
        self.client = topics.make_client("state-manager")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.lock = threading.Lock()
        self.sensors = {}
        self.actuators = {"relay": 0, "led": 0, "buzzer": 0}
        self.previous_breaches = set()
        self.previous_occupied = None
        self.previous_health_bad = None
        self.previous_light_status = None

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(topics.SENSORS_WILDCARD)
        client.subscribe(topics.STATE_ACTUATORS)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if msg.topic == topics.STATE_ACTUATORS:
            with self.lock:
                self.actuators["relay"] = payload.get("relay", self.actuators["relay"])
                self.actuators["led"] = payload.get("led", self.actuators["led"])
                self.actuators["buzzer"] = payload.get("buzzer", self.actuators["buzzer"])
            self.publish_state()
            return
        sensor_id = topics.sensor_id_from_topic(msg.topic)
        if sensor_id is None:
            return
        with self.lock:
            self.sensors[sensor_id] = payload
        self.evaluate_and_publish()

    def get(self, sensor_id, default=None):
        entry = self.sensors.get(sensor_id)
        if entry is None:
            return default
        return entry.get("value", default)

    def compute_breaches(self):
        breaches = set()
        temp = self.get(topics.SENSOR_TEMPERATURE)
        hum = self.get(topics.SENSOR_HUMIDITY)
        co2 = self.get(topics.SENSOR_CO2)
        noise = self.get(topics.SENSOR_NOISE)
        if temp is not None and (temp < COMFORT_TEMP_MIN or temp > COMFORT_TEMP_MAX):
            breaches.add("temperature")
        if hum is not None and (hum < COMFORT_HUM_MIN or hum > COMFORT_HUM_MAX):
            breaches.add("humidity")
        if co2 is not None and co2 >= CO2_WARN:
            breaches.add("co2")
        if noise is not None and noise >= NOISE_WARN:
            breaches.add("noise")
        return breaches

    def health_score(self, breaches):
        return self.productivity(breaches)["score"]

    def productivity(self, breaches):
        """Productivity Score (0-100) with a per-factor breakdown, since the
        project is a *productivity-focused* room — noise counts even though it
        has no actuator."""
        temp = self.get(topics.SENSOR_TEMPERATURE)
        co2 = self.get(topics.SENSOR_CO2)
        factors = []

        def factor(label, deduction, detail):
            factors.append({"label": label, "delta": -deduction if deduction else 0,
                            "ok": deduction == 0, "detail": detail})

        co2_pen = 25 if "co2" in breaches else 0
        if co2 is not None and co2 >= CO2_CRITICAL:
            co2_pen += 15
        factor("Air (CO₂)", co2_pen, f"{co2:.0f} ppm" if co2 is not None else "—")

        temp_pen = 20 if "temperature" in breaches else 0
        if temp is not None and (temp < 16 or temp > 30):
            temp_pen += 10
        factor("Thermal", temp_pen, f"{temp:.1f} °C" if temp is not None else "—")

        factor("Humidity", 10 if "humidity" in breaches else 0,
               f"{self.get(topics.SENSOR_HUMIDITY)} %" if self.get(topics.SENSOR_HUMIDITY) is not None else "—")

        noise = self.get(topics.SENSOR_NOISE)
        factor("Noise", 15 if "noise" in breaches else 0,
               f"{noise:.0f} %" if noise is not None else "—")

        score = max(0, min(100, 100 - sum(-f["delta"] for f in factors)))
        return {"score": score, "factors": factors}

    def build_state(self):
        occupancy = self.sensors.get(topics.SENSOR_OCCUPANCY, {})
        occupied = bool(occupancy.get("occupied", occupancy.get("value", 0)))
        breaches = self.compute_breaches()
        light = self.get(topics.SENSOR_LIGHT)
        noise = self.get(topics.SENSOR_NOISE)
        productivity = self.productivity(breaches)
        state = {
            "ts": time.time(),
            "occupied": occupied,
            "occupancy_distance_cm": occupancy.get("distance_cm"),
            "temperature": self.get(topics.SENSOR_TEMPERATURE),
            "humidity": self.get(topics.SENSOR_HUMIDITY),
            "light": light,
            "noise": noise,
            "co2": self.get(topics.SENSOR_CO2),
            "daylight": bool(self.get(topics.SENSOR_DAYLIGHT, 1)),
            "actuators": dict(self.actuators),
            "breaches": sorted(breaches),
            "health": productivity["score"],
            "health_factors": productivity["factors"],
            "noise_high": "noise" in breaches,
            "comfortable": len(breaches) == 0,
            "light_status": self.light_status(light),
        }
        return state, breaches

    def light_status(self, light):
        if light is None:
            return "unknown"
        if light < LIGHT_LOW:
            return "dark"
        if light > LIGHT_HIGH:
            return "bright"
        return "ok"

    def publish_state(self):
        with self.lock:
            state, _ = self.build_state()
        self.client.publish(topics.STATE_CURRENT, json.dumps(state), retain=True)

    def evaluate_and_publish(self):
        with self.lock:
            state, breaches = self.build_state()
        self.client.publish(topics.STATE_CURRENT, json.dumps(state), retain=True)

        occupied = state["occupied"]
        if self.previous_occupied is not None and occupied != self.previous_occupied:
            self.client.publish(
                topics.EVENT_OCCUPANCY,
                json.dumps({"occupied": occupied, "ts": time.time()}),
            )
        self.previous_occupied = occupied

        # Sound the physical buzzer while the room is in the "critical" health
        # band — but only while someone is in the room to hear it; an empty
        # room stays silent. Publish only on transition so it isn't
        # re-commanded every tick.
        health_bad = occupied and state["health"] < HEALTH_ALARM
        if health_bad != self.previous_health_bad:
            self.client.publish(
                topics.actuator_cmd_topic(topics.ACTUATOR_BUZZER),
                json.dumps({"mode": "beep" if health_bad else "off", "ts": time.time()}),
            )
        self.previous_health_bad = health_bad

        # Light-status transitions (dark ↔ ok ↔ bright) must trigger an
        # immediate replan — e.g. the room lights go out while someone is
        # inside: the planner should switch the lamp on right away, not on the
        # next occupancy change or 60 s tick.
        light_status = state["light_status"]
        if (
            light_status != "unknown"
            and self.previous_light_status not in (None, "unknown")
            and light_status != self.previous_light_status
        ):
            self.client.publish(
                topics.EVENT_LIGHT,
                json.dumps({
                    "status": light_status,
                    "previous": self.previous_light_status,
                    "light": state["light"],
                    "ts": time.time(),
                }),
            )
        if light_status != "unknown":
            self.previous_light_status = light_status

        new_breaches = breaches - self.previous_breaches
        cleared_breaches = self.previous_breaches - breaches
        if new_breaches or cleared_breaches:
            self.client.publish(
                topics.EVENT_THRESHOLD,
                json.dumps({
                    "breaches": sorted(breaches),
                    "new": sorted(new_breaches),
                    "cleared": sorted(cleared_breaches),
                    "ts": time.time(),
                }),
            )
        self.previous_breaches = breaches

    def tick_loop(self):
        while True:
            time.sleep(TICK_INTERVAL)
            self.client.publish(topics.EVENT_TICK, json.dumps({"ts": time.time()}))
            self.publish_state()

    def run(self):
        topics.connect(self.client)
        self.client.loop_start()
        thread = threading.Thread(target=self.tick_loop, daemon=True)
        thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    StateManager().run()


if __name__ == "__main__":
    main()
