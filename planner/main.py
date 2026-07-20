import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import mqtt_topics as topics

DOMAIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "domain.pddl")
FAST_DOWNWARD = os.environ.get("FAST_DOWNWARD", "fast-downward.py")
SEARCH_ALIAS = os.environ.get("FD_ALIAS", "lama-first")

ACTION_TO_ACTUATOR = {
    # Air quality + heating → fan/heater (logical "relay" actuator; no physical
    # relay is wired, so the executor/iot_node just track its state)
    "ventilate": {"actuator": "relay", "state": "on"},
    "heat-room": {"actuator": "relay", "state": "on"},
    "stop-ventilation": {"actuator": "relay", "state": "off"},
    # Cooling → simulated AC
    "cool-room": {"actuator": "ac", "state": "cooling"},
    "stop-cooling": {"actuator": "ac", "state": "off"},
    # Blinds → daylight + solar-heat management
    "open-blinds-for-daylight": {"actuator": "blinds", "position": 100},
    "close-blinds-for-cooling": {"actuator": "blinds", "position": 0},
    "close-blinds": {"actuator": "blinds", "position": 0},
    # Room lamp → Plugwise socket (physical lamp, switched via the bridge)
    "turn-on-lamp-night": {"actuator": "socket", "state": "on"},
    "turn-on-lamp-hot": {"actuator": "socket", "state": "on"},
    "turn-off-lamp": {"actuator": "socket", "state": "off"},
}


class Planner:
    def __init__(self):
        self.client = topics.make_client("planner")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(topics.PLANNING_PROBLEM)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        problem = payload.get("problem")
        if not problem:
            return
        actions = self.solve(problem)
        self.publish_plan(payload, actions)

    def solve(self, problem_text):
        actions = self.run_fast_downward(problem_text)
        if actions is None:
            actions = self.fallback_solve(problem_text)
        return actions

    def run_fast_downward(self, problem_text):
        workdir = tempfile.mkdtemp(prefix="fd-")
        problem_path = os.path.join(workdir, "problem.pddl")
        plan_path = os.path.join(workdir, "plan.out")
        with open(problem_path, "w") as handle:
            handle.write(problem_text)
        cmd = [
            FAST_DOWNWARD,
            "--alias",
            SEARCH_ALIAS,
            "--plan-file",
            plan_path,
            DOMAIN_PATH,
            problem_path,
        ]
        try:
            subprocess.run(
                cmd,
                cwd=workdir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if not os.path.exists(plan_path):
            return None
        return self.parse_plan_file(plan_path)

    def parse_plan_file(self, plan_path):
        actions = []
        with open(plan_path) as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                tokens = line.strip("()").split()
                if tokens:
                    actions.append(tokens[0])
        return actions

    def fallback_solve(self, problem_text):
        facts = set(re.findall(r"\(([a-z0-9\-]+) room1\)", problem_text))
        goal_section = problem_text.split(":goal", 1)[-1]
        goals = set(re.findall(r"\(([a-z0-9\-]+) room1\)", goal_section))
        plan = []

        def has(fact):
            return fact in facts

        # ── Empty room → shut everything off ────────────────────────────
        if "energy-saving" in goals:
            if has("lamp-on"):
                plan.append("turn-off-lamp")
            if has("fan-on"):
                plan.append("stop-ventilation")
            if has("ac-cooling"):
                plan.append("stop-cooling")
            if has("blinds-open"):
                plan.append("close-blinds")
            plan.append("achieve-energy-saving")
            return plan

        # ── Occupied room → comfort & productivity ──────────────────────
        # Air quality: fan clears CO2
        if has("co2-high"):
            plan.append("ventilate")

        # Temperature: block solar heat (close blinds) BEFORE cooling.
        if has("temp-hot"):
            if has("blinds-open"):
                plan.append("close-blinds-for-cooling")
            plan.append("cool-room")
        elif has("ac-cooling") and has("temp-comfortable"):
            plan.append("stop-cooling")

        if has("temp-cold"):
            plan.append("heat-room")

        # Lighting: only act when the room is actually dark.
        # Prefer FREE daylight (open blinds) when it's daytime and not hot;
        # otherwise fall back to the lamp.
        if has("ambient-dark"):
            opened_blinds = False
            if (
                has("blinds-closed")
                and has("daylight-available")
                and not has("temp-hot")
            ):
                plan.append("open-blinds-for-daylight")
                opened_blinds = True
            if not opened_blinds and has("lamp-off"):
                if has("temp-hot"):
                    plan.append("turn-on-lamp-hot")
                else:
                    plan.append("turn-on-lamp-night")

        plan.append("achieve-comfort")
        return plan

    def to_commands(self, actions):
        commands = []
        for action in actions:
            mapping = ACTION_TO_ACTUATOR.get(action)
            if mapping:
                commands.append({"action": action, **mapping})
            else:
                commands.append({"action": action})
        return commands

    def publish_plan(self, problem_payload, actions):
        message = {
            "ts": time.time(),
            "trigger": problem_payload.get("trigger"),
            "goal": problem_payload.get("goal"),
            "actions": actions,
            "steps": self.to_commands(actions),
            "length": len(actions),
        }
        self.client.publish(topics.PLANNING_PLAN, json.dumps(message), retain=True)

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
    Planner().run()


if __name__ == "__main__":
    main()
