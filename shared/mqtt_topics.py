import os

import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = int(os.environ.get("MQTT_KEEPALIVE", "60"))

SENSORS_BASE = "sensors"
ACTUATORS_BASE = "actuators"

SENSOR_TEMPERATURE = "temperature"
SENSOR_HUMIDITY = "humidity"
SENSOR_LIGHT = "light"
SENSOR_NOISE = "noise"
SENSOR_OCCUPANCY = "occupancy"
SENSOR_CO2 = "co2"
SENSOR_DAYLIGHT = "daylight"

ACTUATOR_RELAY = "relay"
ACTUATOR_LED = "led"
ACTUATOR_BUZZER = "buzzer"
ACTUATOR_AC = "ac"
ACTUATOR_BLINDS = "blinds"
ACTUATOR_SOCKET = "socket"

SENSORS_WILDCARD = "sensors/#"
ACTUATORS_CMD_WILDCARD = "actuators/+/cmd"

STATE_CURRENT = "state/current"
STATE_ACTUATORS = "state/actuators"
STATE_SIMULATED = "state/simulated"

# Retained map of manually-held sensor values: {"values": {sensor_id: value}}.
# A sensor listed here is pinned; absence means "use the live reading".
OVERRIDE_SENSORS = "override/sensors"

PLANNING_PROBLEM = "planning/problem"
PLANNING_PLAN = "planning/plan"

EVENTS_WILDCARD = "events/#"
EVENT_OCCUPANCY = "events/occupancy"
EVENT_THRESHOLD = "events/threshold"
EVENT_TICK = "events/tick"
EVENT_MANUAL = "events/manual"
EVENT_REPLAN = "events/replan"
EVENT_EXECUTED = "events/executed"
EVENT_PLAN_DONE = "events/plan_done"
EVENT_OVERRIDE = "events/override"
# Light-status band changed (dark/ok/bright) — triggers an immediate replan so
# the lamp reacts to darkness without waiting for an occupancy event or tick.
EVENT_LIGHT = "events/light"

# The room lamp is the only *physical* switched load (Plugwise socket). The LED
# and buzzer are physical status indicators on the Grove board. The "relay" is
# kept as a logical fan/heater actuator only — there is no physical relay wired,
# so on real hardware it is never written to a GPIO pin (see iot_node/actuators).
REAL_ACTUATORS = {ACTUATOR_RELAY, ACTUATOR_LED, ACTUATOR_BUZZER}
SIMULATED_ACTUATORS = {ACTUATOR_AC, ACTUATOR_BLINDS, ACTUATOR_SOCKET}


def sensor_topic(sensor_id):
    return f"{SENSORS_BASE}/{sensor_id}"


def actuator_cmd_topic(actuator_id):
    return f"{ACTUATORS_BASE}/{actuator_id}/cmd"


def sensor_id_from_topic(topic):
    parts = topic.split("/")
    if len(parts) == 2 and parts[0] == SENSORS_BASE:
        return parts[1]
    return None


def actuator_id_from_topic(topic):
    parts = topic.split("/")
    if len(parts) == 3 and parts[0] == ACTUATORS_BASE and parts[2] == "cmd":
        return parts[1]
    return None


def make_client(client_id):
    try:
        return mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)


def connect(client, host=None, port=None, keepalive=None):
    client.connect(
        host or MQTT_HOST,
        port or MQTT_PORT,
        keepalive or MQTT_KEEPALIVE,
    )
    return client
