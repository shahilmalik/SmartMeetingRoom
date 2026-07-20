import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

ROOM = "room1"

COMFORT_TEMP_MIN = 20.0
COMFORT_TEMP_MAX = 24.0
CO2_HIGH = 1000.0


class ProblemGenerator:
    def __init__(self):
        self.client = topics.make_client("problem-generator")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.latest_state = None
        self.latest_simulated = {}

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(topics.STATE_CURRENT)
        client.subscribe(topics.STATE_SIMULATED)
        client.subscribe(topics.EVENT_OCCUPANCY)
        client.subscribe(topics.EVENT_THRESHOLD)
        client.subscribe(topics.EVENT_TICK)
        client.subscribe(topics.EVENT_MANUAL)
        client.subscribe(topics.EVENT_OVERRIDE)
        client.subscribe(topics.EVENT_LIGHT)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if msg.topic == topics.STATE_CURRENT:
            self.latest_state = payload
            return
        if msg.topic == topics.STATE_SIMULATED:
            self.latest_simulated = payload
            return
        if self.latest_state is not None:
            self.generate_and_publish(msg.topic)

    def temp_predicate(self, temp):
        if temp is None:
            return "temp-comfortable"
        if temp > COMFORT_TEMP_MAX:
            return "temp-hot"
        if temp < COMFORT_TEMP_MIN:
            return "temp-cold"
        return "temp-comfortable"

    def build_init(self, state):
        occupied = bool(state.get("occupied"))
        actuators = state.get("actuators", {})
        relay = actuators.get("relay", 0)
        co2 = state.get("co2")

        facts = []
        facts.append("occupied" if occupied else "empty")
        facts.append(self.temp_predicate(state.get("temperature")))

        if co2 is not None and co2 >= CO2_HIGH:
            facts.append("co2-high")
        else:
            facts.append("co2-ok")

        # Ambient light comes straight from the sensor's status band.
        light_status = state.get("light_status", "ok")
        if light_status == "dark":
            facts.append("ambient-dark")
        elif light_status == "bright":
            facts.append("ambient-bright")
        else:
            facts.append("ambient-ok")
        # The room is "lit" whenever the light sensor is not dark — this is the
        # ground truth regardless of whether the source is daylight or the lamp.
        if light_status != "dark":
            facts.append("room-lit")

        # Daylight availability (time-of-day, overridable) decides whether
        # opening the blinds would actually help.
        facts.append("daylight-available" if state.get("daylight") else "no-daylight")

        # Fan/heater = Grove relay; AC + blinds + lamp = simulated actuators.
        facts.append("fan-on" if relay else "fan-off")
        facts.append("ac-cooling" if self.latest_simulated.get("ac") == "cooling" else "ac-off")
        facts.append("blinds-open" if (self.latest_simulated.get("blinds", 0) or 0) > 0 else "blinds-closed")
        facts.append("lamp-on" if self.latest_simulated.get("socket") == "on" else "lamp-off")

        return facts

    def build_goal(self, state):
        if bool(state.get("occupied")):
            return ["comfortable"]
        return ["energy-saving"]

    def render(self, state):
        init_facts = self.build_init(state)
        goal_facts = self.build_goal(state)
        init_str = "\n    ".join(f"({fact} {ROOM})" for fact in init_facts)
        goal_str = "\n      ".join(f"({fact} {ROOM})" for fact in goal_facts)
        problem = (
            "(define (problem meeting-room-state)\n"
            "  (:domain smart-meeting-room)\n"
            f"  (:objects {ROOM} - room)\n"
            "  (:init\n"
            f"    {init_str}\n"
            "  )\n"
            "  (:goal (and\n"
            f"      {goal_str}\n"
            "    )\n"
            "  )\n"
            ")\n"
        )
        return problem

    def generate_and_publish(self, trigger):
        state = self.latest_state
        problem = self.render(state)
        message = {
            "ts": time.time(),
            "trigger": trigger,
            "goal": "comfort" if state.get("occupied") else "energy-saving",
            "problem": problem,
        }
        self.client.publish(topics.PLANNING_PROBLEM, json.dumps(message))

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
    ProblemGenerator().run()


if __name__ == "__main__":
    main()
