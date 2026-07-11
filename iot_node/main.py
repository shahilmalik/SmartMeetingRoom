import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

if __package__ in (None, ""):
    import hardware
    import sensors
    from actuators import Actuators
else:
    from . import hardware
    from . import sensors
    from .actuators import Actuators

PUBLISH_INTERVAL = float(os.environ.get("IOT_INTERVAL", "2.0"))
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))


def log(msg):
    print(f"[iot_node] {msg}", file=sys.stderr, flush=True)


class IoTNode:
    def __init__(self):
        self.client = topics.make_client("iot-node")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.actuators = Actuators()
        self.last_button = 0
        self.last_occupied = None
        self._connected = False

    def on_connect(self, client, userdata, flags, rc):
        self._connected = True
        log(f"MQTT connected (rc={rc})")
        client.subscribe(topics.ACTUATORS_CMD_WILDCARD)

    def on_disconnect(self, client, userdata, rc):
        self._connected = False
        log(f"MQTT disconnected (rc={rc}), will auto-reconnect")

    def on_message(self, client, userdata, msg):
        actuator_id = topics.actuator_id_from_topic(msg.topic)
        if actuator_id is None:
            return
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        result = self.actuators.apply_command(actuator_id, payload)
        if result:
            self.publish_actuator_state()

    def publish(self, sensor_id, value, extra=None):
        payload = {"id": sensor_id, "value": value, "ts": time.time()}
        if extra:
            payload.update(extra)
        self.client.publish(topics.sensor_topic(sensor_id), json.dumps(payload), retain=True)

    def publish_actuator_state(self):
        self.client.publish(
            topics.STATE_ACTUATORS,
            json.dumps({"ts": time.time(), **self.actuators.snapshot()}),
            retain=True,
        )

    def poll_once(self):
        temp, hum = sensors.read_temperature_humidity()
        if temp is not None:
            self.publish(topics.SENSOR_TEMPERATURE, temp, {"unit": "C"})
        if hum is not None:
            self.publish(topics.SENSOR_HUMIDITY, hum, {"unit": "%"})
        log(f"temp={temp} hum={hum}")

        light_raw, light_pct = sensors.read_light()
        self.publish(topics.SENSOR_LIGHT, light_pct, {"raw": light_raw, "unit": "%"})
        log(f"light={light_pct}% raw={light_raw}")

        noise_raw, noise_pct = sensors.read_noise()
        self.publish(topics.SENSOR_NOISE, noise_pct, {"raw": noise_raw, "unit": "%"})
        log(f"noise={noise_pct}% raw={noise_raw}")

        occupied, distance = sensors.read_occupancy()
        button = sensors.read_button()
        if button and not self.last_button:
            occupied = not occupied
            self.client.publish(topics.EVENT_MANUAL, json.dumps({"source": "button", "ts": time.time()}))
        self.last_button = button

        self.publish(
            topics.SENSOR_OCCUPANCY,
            1 if occupied else 0,
            {"distance_cm": distance, "occupied": occupied},
        )
        if self.last_occupied is not None and occupied != self.last_occupied:
            self.client.publish(
                topics.EVENT_OCCUPANCY,
                json.dumps({"occupied": occupied, "ts": time.time()}),
            )
        self.last_occupied = occupied
        log(f"occupancy={occupied} dist={distance}cm btn={button}")

        co2 = sensors.read_co2(occupied)
        self.publish(topics.SENSOR_CO2, co2, {"unit": "ppm"})
        log(f"co2={co2}ppm (simulated)")

    def run(self):
        hardware.setup()
        log(f"Connecting to broker {MQTT_HOST}:{MQTT_PORT}")
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)
        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()
        self.publish_actuator_state()
        fail_count = 0
        try:
            while True:
                try:
                    self.poll_once()
                    fail_count = 0
                except Exception as e:
                    fail_count += 1
                    log(f"poll_once error #{fail_count}: {e}")
                    if fail_count >= 10:
                        log("Too many consecutive errors, sleeping 30s")
                        time.sleep(30)
                        fail_count = 0
                time.sleep(PUBLISH_INTERVAL)
        except KeyboardInterrupt:
            log("Shutting down")
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    IoTNode().run()


if __name__ == "__main__":
    main()
