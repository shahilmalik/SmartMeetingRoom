import json
import os
import sys
import threading
import time
from collections import deque

import paho.mqtt.client as mqtt

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, REPO_ROOT)

from shared import mqtt_topics as topics

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
EVENT_LIMIT = int(os.environ.get("EVENT_HISTORY_LIMIT", "100"))


class MqttStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.sensors = {}
        self.state = {}
        self.plan = {}
        self.simulated = {}
        self.events = deque(maxlen=EVENT_LIMIT)
        self.connected = False
        self.client = None
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        self.client = topics.make_client(f"dashboard-backend-{os.getpid()}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        while True:
            try:
                self.client.connect(MQTT_HOST, MQTT_PORT, 60)
                self.client.loop_forever()
            except Exception:
                self.connected = False
                time.sleep(3)

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = True
        client.subscribe(topics.SENSORS_WILDCARD)
        client.subscribe(topics.STATE_CURRENT)
        client.subscribe(topics.PLANNING_PLAN)
        client.subscribe(topics.EVENTS_WILDCARD)
        client.subscribe(topics.STATE_SIMULATED)
        client.subscribe(topics.STATE_ACTUATORS)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        topic = msg.topic
        with self.lock:
            if topic == topics.STATE_CURRENT:
                self.state = payload
            elif topic == topics.PLANNING_PLAN:
                self.plan = payload
            elif topic == topics.STATE_SIMULATED:
                self.simulated = payload
            elif topic == topics.STATE_ACTUATORS:
                self.state.setdefault("actuators", {})
                self.state["actuators"].update(
                    {"relay": payload.get("relay"), "led": payload.get("led")}
                )
            elif topic.startswith("sensors/"):
                sensor_id = topics.sensor_id_from_topic(topic)
                if sensor_id:
                    self.sensors[sensor_id] = payload
            elif topic.startswith("events/"):
                self.events.appendleft(
                    {"topic": topic, "payload": payload, "received": time.time()}
                )

    def publish(self, topic, payload):
        if self.client is None:
            return False
        self.client.publish(topic, json.dumps(payload))
        return True

    def snapshot(self):
        with self.lock:
            return {
                "connected": self.connected,
                "sensors": dict(self.sensors),
                "state": dict(self.state),
                "plan": dict(self.plan),
                "simulated": dict(self.simulated),
                "events": list(self.events),
            }


store = MqttStore()
