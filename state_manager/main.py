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


class StateManager:
    def __init__(self):
        self.client = topics.make_client("state-manager")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.lock = threading.Lock()
        self.sensors = {}
        self.actuators = {"relay": 0, "led": 0}
        self.previous_breaches = set()

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
        score = 100
        temp = self.get(topics.SENSOR_TEMPERATURE)
        co2 = self.get(topics.SENSOR_CO2)
        if "temperature" in breaches:
            score -= 20
        if "humidity" in breaches:
            score -= 10
        if "co2" in breaches:
            score -= 25
        if co2 is not None and co2 >= CO2_CRITICAL:
            score -= 15
        if "noise" in breaches:
            score -= 10
        if temp is not None and (temp < 16 or temp > 30):
            score -= 10
        return max(0, min(100, score))

    def build_state(self):
        occupancy = self.sensors.get(topics.SENSOR_OCCUPANCY, {})
        occupied = bool(occupancy.get("occupied", occupancy.get("value", 0)))
        breaches = self.compute_breaches()
        light = self.get(topics.SENSOR_LIGHT)
        state = {
            "ts": time.time(),
            "occupied": occupied,
            "occupancy_distance_cm": occupancy.get("distance_cm"),
            "temperature": self.get(topics.SENSOR_TEMPERATURE),
            "humidity": self.get(topics.SENSOR_HUMIDITY),
            "light": light,
            "noise": self.get(topics.SENSOR_NOISE),
            "co2": self.get(topics.SENSOR_CO2),
            "actuators": dict(self.actuators),
            "breaches": sorted(breaches),
            "health": self.health_score(breaches),
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
        new_breaches = breaches - self.previous_breaches
        if new_breaches:
            self.client.publish(
                topics.EVENT_THRESHOLD,
                json.dumps({"breaches": sorted(new_breaches), "ts": time.time()}),
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
