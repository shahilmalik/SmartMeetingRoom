import json
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

DAY_START_HOUR = int(os.environ.get("DAYLIGHT_START_HOUR", "7"))
DAY_END_HOUR = int(os.environ.get("DAYLIGHT_END_HOUR", "19"))


def is_daytime():
    hour = datetime.now().hour
    return DAY_START_HOUR <= hour < DAY_END_HOUR

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

# Noise level (0-100 %) at/above which the status LED blinks. Matches the
# State Manager's NOISE_WARN so the physical indicator and dashboard agree.
NOISE_WARN = float(os.environ.get("NOISE_WARN", "65"))


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
        # Manually-held sensor values ({sensor_id: value}); empty = all live.
        self.overrides = {}
        # Room lamp (Plugwise socket) state, tracked from state/simulated so the
        # physical button can toggle it. Optimistically updated on button press.
        self.socket_state = "off"
        # Status-indicator modes realised by the indicator thread.
        self.led_mode = "off"     # "off" | "blink"  (blinks on high noise)
        self.buzzer_mode = "off"  # "off" | "beep"   (beeps on bad health)
        # Manual hardware-test overrides (epoch until which the indicator is
        # forced on, regardless of noise/health) — driven by the dashboard's
        # actuator test drawer so you can verify the wiring on demand.
        self.led_test_until = 0.0
        self.buzzer_test_until = 0.0
        self._ind_lock = threading.Lock()

    def _led_active(self):
        return self.led_mode == "blink" or time.time() < self.led_test_until

    def _buzzer_active(self):
        return self.buzzer_mode == "beep" or time.time() < self.buzzer_test_until

    def on_connect(self, client, userdata, flags, rc):
        self._connected = True
        log(f"MQTT connected (rc={rc})")
        client.subscribe(topics.ACTUATORS_CMD_WILDCARD)
        client.subscribe(topics.OVERRIDE_SENSORS)
        client.subscribe(topics.STATE_SIMULATED)

    def on_disconnect(self, client, userdata, rc):
        self._connected = False
        log(f"MQTT disconnected (rc={rc}), will auto-reconnect")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if msg.topic == topics.OVERRIDE_SENSORS:
            self.overrides = payload.get("values", {}) or {}
            log(f"sensor overrides = {self.overrides}")
            # Nudge the pipeline so a held value is reflected immediately.
            self.client.publish(topics.EVENT_OVERRIDE, json.dumps({"ts": time.time()}))
            return
        if msg.topic == topics.STATE_SIMULATED:
            self.socket_state = str(payload.get("socket", self.socket_state)).lower()
            hardware.set_sim_environment(
                blinds=payload.get("blinds"),
                ac=payload.get("ac"),
                socket=payload.get("socket"),
            )
            return
        actuator_id = topics.actuator_id_from_topic(msg.topic)
        if actuator_id is None:
            return
        if actuator_id == "test":
            # Manual hardware test from the dashboard drawer: force one
            # indicator on for a short duration via the real write path.
            self.start_test(str(payload.get("target", "")).lower(),
                            float(payload.get("duration", 2.0)))
            return
        if actuator_id == topics.ACTUATOR_BUZZER:
            mode = str(payload.get("mode", payload.get("state", "off"))).lower()
            with self._ind_lock:
                self.buzzer_mode = "beep" if mode in ("beep", "on", "1", "true") else "off"
            self.publish_actuator_state()
            return
        if actuator_id == topics.ACTUATOR_LED:
            mode = str(payload.get("mode", payload.get("state", "off"))).lower()
            with self._ind_lock:
                self.led_mode = "blink" if mode in ("blink", "on", "1", "true") else "off"
            self.publish_actuator_state()
            return
        result = self.actuators.apply_command(actuator_id, payload)
        if result:
            self.publish_actuator_state()

    def toggle_lamp(self):
        """Physical button acts as the room-light switch: flip the Plugwise
        socket and let the executor + bridge + dashboard react."""
        new_state = "off" if self.socket_state == "on" else "on"
        self.socket_state = new_state  # optimistic; confirmed by state/simulated
        self.client.publish(
            topics.actuator_cmd_topic(topics.ACTUATOR_SOCKET),
            json.dumps({"state": new_state, "source": "button", "ts": time.time()}),
        )
        log(f"button → lamp {new_state}")

    def start_test(self, target, duration=2.0):
        """Force an indicator on for `duration` seconds so its wiring can be
        verified from the dashboard. Uses the same indicator thread + real
        write path as the live noise/health behaviour."""
        duration = max(0.2, min(10.0, duration))
        until = time.time() + duration
        with self._ind_lock:
            if target == "led":
                self.led_test_until = until
            elif target == "buzzer":
                self.buzzer_test_until = until
            else:
                return
        log(f"test {target} for {duration:.1f}s")
        self.publish_actuator_state()

    def ov(self, sensor_id, live):
        """Return a held override for this sensor if present, else the live value."""
        if sensor_id in self.overrides and self.overrides[sensor_id] is not None:
            return self.overrides[sensor_id]
        return live

    def publish(self, sensor_id, value, extra=None):
        payload = {"id": sensor_id, "value": value, "ts": time.time()}
        if extra:
            payload.update(extra)
        self.client.publish(topics.sensor_topic(sensor_id), json.dumps(payload), retain=True)

    def publish_actuator_state(self):
        # Report the indicator *intent* (steady on/off) rather than the
        # instantaneous blink/beep toggle, so the dashboard reads cleanly.
        snap = dict(self.actuators.snapshot())
        snap["led"] = 255 if self._led_active() else 0
        snap["buzzer"] = 1 if self._buzzer_active() else 0
        self.client.publish(
            topics.STATE_ACTUATORS,
            json.dumps({"ts": time.time(), **snap}),
            retain=True,
        )

    def indicator_loop(self):
        """Realise the LED (noise) and buzzer (health) indicator patterns.
        Writes only happen on a value change, so an idle system is silent."""
        phase = 0
        last_led = None
        last_buzz = None
        prev_active = None
        while True:
            with self._ind_lock:
                led_active = self._led_active()
                buzz_active = self._buzzer_active()
            led_val = 255 if (led_active and phase % 2 == 0) else 0
            buzz_val = 1 if (buzz_active and phase % 3 == 0) else 0
            if led_val != last_led:
                try:
                    self.actuators.set_led(led_val)
                except Exception as e:
                    log(f"led write failed: {e}")
                last_led = led_val
            if buzz_val != last_buzz:
                try:
                    self.actuators.set_buzzer(buzz_val)
                except Exception as e:
                    log(f"buzzer write failed: {e}")
                last_buzz = buzz_val
            if (led_active, buzz_active) != prev_active:
                self.publish_actuator_state()
                prev_active = (led_active, buzz_active)
            phase += 1
            time.sleep(0.3)

    def self_test(self):
        """Blink the LED and chirp the buzzer once at startup so a wired
        indicator visibly/audibly confirms it responds."""
        try:
            self.actuators.set_led(255)
            time.sleep(0.3)
            self.actuators.set_led(0)
            self.actuators.set_buzzer(1)
            time.sleep(0.15)
            self.actuators.set_buzzer(0)
        except Exception as e:
            log(f"self-test failed: {e}")

    def poll_once(self):
        # Daylight: time-of-day by default, but a held override wins so the
        # dashboard can force day/night during a demo. Feed it into the sim.
        daylight = bool(self.ov(topics.SENSOR_DAYLIGHT, 1 if is_daytime() else 0))
        hardware.set_sim_environment(daylight=daylight)
        self.publish(topics.SENSOR_DAYLIGHT, 1 if daylight else 0)

        temp, hum = sensors.read_temperature_humidity()
        temp = self.ov(topics.SENSOR_TEMPERATURE, temp)
        hum = self.ov(topics.SENSOR_HUMIDITY, hum)
        if temp is not None:
            self.publish(topics.SENSOR_TEMPERATURE, temp, {"unit": "C"})
        if hum is not None:
            self.publish(topics.SENSOR_HUMIDITY, hum, {"unit": "%"})
        log(f"temp={temp} hum={hum}")

        light_raw, light_pct = sensors.read_light()
        light_pct = self.ov(topics.SENSOR_LIGHT, light_pct)
        self.publish(topics.SENSOR_LIGHT, light_pct, {"raw": light_raw, "unit": "%"})
        log(f"light={light_pct}% raw={light_raw} day={daylight}")

        noise_raw, noise_pct = sensors.read_noise()
        noise_pct = self.ov(topics.SENSOR_NOISE, noise_pct)
        self.publish(topics.SENSOR_NOISE, noise_pct, {"raw": noise_raw, "unit": "%"})
        log(f"noise={noise_pct}% raw={noise_raw}")

        occupied, distance = sensors.read_occupancy()
        button = sensors.read_button()
        if button and not self.last_button:
            # The physical button is the room-light switch (toggles the lamp).
            self.toggle_lamp()
        self.last_button = button
        if topics.SENSOR_OCCUPANCY in self.overrides and self.overrides[topics.SENSOR_OCCUPANCY] is not None:
            occupied = bool(self.overrides[topics.SENSOR_OCCUPANCY])
            distance = 8 if occupied else 150

        # Blink the status LED when the room is too loud — but only while
        # someone is actually there to see it; an empty room stays dark.
        with self._ind_lock:
            self.led_mode = (
                "blink"
                if (occupied and noise_pct is not None and noise_pct >= NOISE_WARN)
                else "off"
            )

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

        ventilating = bool(self.actuators.relay_state)
        co2 = sensors.read_co2(occupied, ventilating=ventilating)
        co2 = self.ov(topics.SENSOR_CO2, co2)
        self.publish(topics.SENSOR_CO2, co2, {"unit": "ppm"})
        log(f"co2={co2}ppm vent={ventilating} (simulated)")

    def run(self):
        hardware.setup()
        log(f"Connecting to broker {MQTT_HOST}:{MQTT_PORT}")
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)
        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()
        self.self_test()
        self.publish_actuator_state()
        threading.Thread(target=self.indicator_loop, daemon=True).start()
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
