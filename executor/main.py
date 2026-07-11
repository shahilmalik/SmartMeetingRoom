import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

STEP_DELAY = float(os.environ.get("EXECUTOR_STEP_DELAY", "1.0"))


class SimulatedActuators:
    def __init__(self):
        self.ac = "off"
        self.blinds = 0
        self.socket = "off"

    def apply(self, step):
        actuator = step.get("actuator")
        if actuator == "ac":
            self.ac = step.get("state", self.ac)
            return True
        if actuator == "blinds":
            self.blinds = step.get("position", self.blinds)
            return True
        if actuator == "socket":
            self.socket = step.get("state", self.socket)
            return True
        return False

    def snapshot(self):
        return {"ac": self.ac, "blinds": self.blinds, "socket": self.socket}


class Executor:
    def __init__(self):
        self.client = topics.make_client("executor")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sim = SimulatedActuators()
        self.lock = threading.Lock()
        self.current_plan_ts = None

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(topics.PLANNING_PLAN)
        client.subscribe(topics.actuator_cmd_topic(topics.ACTUATOR_AC))
        client.subscribe(topics.actuator_cmd_topic(topics.ACTUATOR_BLINDS))
        client.subscribe(topics.actuator_cmd_topic(topics.ACTUATOR_SOCKET))

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        actuator_id = topics.actuator_id_from_topic(msg.topic)
        if actuator_id in topics.SIMULATED_ACTUATORS:
            self.sim.apply({"actuator": actuator_id, **payload})
            self.publish_progress({"action": f"manual-{actuator_id}"})
            return
        with self.lock:
            if payload.get("ts") == self.current_plan_ts:
                return
            self.current_plan_ts = payload.get("ts")
        thread = threading.Thread(target=self.execute_plan, args=(payload,), daemon=True)
        thread.start()

    def send_real(self, actuator_id, command):
        self.client.publish(topics.actuator_cmd_topic(actuator_id), json.dumps(command))

    def execute_step(self, step):
        actuator = step.get("actuator")
        if actuator == "relay":
            self.send_real("relay", {"state": step.get("state", "off")})
        elif actuator == "led":
            self.send_real("led", {"brightness": step.get("brightness", 0)})
        elif actuator in ("ac", "blinds", "socket"):
            self.sim.apply(step)
        self.publish_progress(step)

    def publish_progress(self, step):
        message = {
            "ts": time.time(),
            "executed": step.get("action"),
            "simulated": self.sim.snapshot(),
        }
        self.client.publish(topics.EVENT_EXECUTED, json.dumps(message))
        self.client.publish(
            topics.STATE_SIMULATED,
            json.dumps({"ts": time.time(), **self.sim.snapshot()}),
            retain=True,
        )

    def execute_plan(self, payload):
        steps = payload.get("steps", [])
        for step in steps:
            self.execute_step(step)
            time.sleep(STEP_DELAY)
        self.client.publish(
            topics.EVENT_PLAN_DONE,
            json.dumps({"ts": time.time(), "length": len(steps), "goal": payload.get("goal")}),
        )

    def run(self):
        topics.connect(self.client)
        self.client.loop_start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def main():
    Executor().run()


if __name__ == "__main__":
    main()
