#!/usr/bin/env python3
"""
Plugwise USB bridge — runs on the HOST Mac, NOT inside Docker.

Subscribes to MQTT actuators/socket/cmd and physically switches the
Plugwise Circle / Circle+ (room lamp).

Install:
    pip3 install python-plugwise paho-mqtt

Usage (normal):
    python3 plugwise_bridge.py

Usage (force re-pair):
    PAIR=1 python3 plugwise_bridge.py
    Then press the button on the Circle+ until it blinks.
"""

import json
import logging
import os
import queue
import threading
import time

import paho.mqtt.client as mqtt
from plugwise.messages.requests import CircleSwitchRelayRequest
from plugwise.stick import stick as Stick

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("plugwise-bridge")

PORT      = os.environ.get("PLUGWISE_PORT", "/dev/cu.usbserial-A6010L0M")
CIRCLE_MAC = os.environ.get("CIRCLE_MAC", "000D6F000567156D")
MQTT_HOST  = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT  = int(os.environ.get("MQTT_PORT", "1883"))
PAIR_MODE  = os.environ.get("PAIR", "0") == "1"
CMD_TOPIC  = "actuators/socket/cmd"

_cmd_q: queue.Queue = queue.Queue()
_stick_ref = None
_mac_bytes: bytes = b""

# Track last state sent to the relay so we skip no-op duplicate commands.
# None means "unknown" — the first state/simulated retained message on
# startup is used to sync without sending a relay command.
_last_relay_state = None  # type: ignore
_state_synced = False          # True once we've absorbed the retained state


# ── MQTT ──────────────────────────────────────────────────────────────────────

STATE_SIMULATED_TOPIC = "state/simulated"


def _on_connect(client, userdata, flags, rc):
    client.subscribe(CMD_TOPIC)
    client.subscribe(STATE_SIMULATED_TOPIC)
    log.info("MQTT connected → subscribed to %s and %s", CMD_TOPIC, STATE_SIMULATED_TOPIC)


def _on_message(client, userdata, msg):
    global _last_relay_state, _state_synced

    try:
        payload = json.loads(msg.payload.decode())
    except (ValueError, UnicodeDecodeError):
        return

    if msg.topic == STATE_SIMULATED_TOPIC:
        # Planner-driven path: executor updates sim and publishes here.
        socket_state = str(payload.get("socket", "off")).lower()
        if not _state_synced:
            # Absorb the retained message on startup — don't send a relay
            # command, just record current state so we detect future changes.
            _last_relay_state = socket_state
            _state_synced = True
            log.info("Synced initial socket state from state/simulated: %s", socket_state)
            return
        if socket_state != _last_relay_state:
            _last_relay_state = socket_state
            _cmd_q.put(socket_state)
            log.info("Queued (state/simulated): socket → %s", socket_state)
        return

    # actuators/socket/cmd — manual command from the dashboard Controls panel
    state = str(payload.get("state", "")).lower()
    if state not in ("on", "off"):
        # "auto" (planner-release) and any unknown state are not physical
        # switches — ignore them so the relay isn't toggled by mistake.
        return
    if state != _last_relay_state:
        _last_relay_state = state
        _cmd_q.put(state)
        log.info("Queued (cmd): socket → %s", state)


def _mqtt_thread():
    # Unique per-process id: two clients sharing one id make the broker kick
    # them in a loop (a ~2s reconnect storm), during which QoS-0 commands get
    # dropped and the lamp never switches.
    client_id = f"plugwise-bridge-{os.getpid()}"
    try:
        client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=client_id)

    client.on_connect = _on_connect
    client.on_message = _on_message
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            log.warning("MQTT error (%s) — retry in 5 s", e)
            time.sleep(5)


# ── Plugwise ──────────────────────────────────────────────────────────────────

def _switch(on: bool):
    req = CircleSwitchRelayRequest(_mac_bytes, on)
    _stick_ref.send(req)
    log.info("Sent CircleSwitchRelayRequest → %s", "ON" if on else "OFF")


def _do_pairing(s):
    """Enable join mode and wait for the Circle+ to announce itself."""
    log.info("=" * 60)
    log.info("PAIRING MODE")
    log.info("  1. Press and hold the button on the Plugwise Circle+")
    log.info("     until its LED blinks (usually 5-10 seconds).")
    log.info("  2. Release the button.")
    log.info("  Waiting up to 120 seconds for join request …")
    log.info("=" * 60)

    joined = threading.Event()
    joined_mac = [None]

    def _join_cb(mac):
        log.info("Join request received from %s — accepting …", mac)
        joined_mac[0] = mac
        joined.set()

    # Override the auto-join callback so we can detect it
    original_cb = s.do_callback

    def _patched_cb(cb_type, mac=None, *args, **kwargs):
        from plugwise.constants import CB_JOIN_REQUEST
        if cb_type == CB_JOIN_REQUEST and mac:
            _join_cb(mac)
        else:
            original_cb(cb_type, mac, *args, **kwargs)

    s.do_callback = _patched_cb
    s.allow_join_requests(True, True)   # broadcast open network + auto-accept

    if joined.wait(timeout=180):
        log.info("Paired with %s — testing switch …", joined_mac[0])
        time.sleep(2)
        s.allow_join_requests(False, False)
        return joined_mac[0]
    else:
        log.warning("No join request received in 180 s. "
                    "Try PAIR=1 python3 plugwise_bridge.py again.")
        s.allow_join_requests(False, False)
        return None


def _main():
    global _stick_ref, _mac_bytes

    mac_str = CIRCLE_MAC.upper().replace(":", "").replace("-", "")
    _mac_bytes = mac_str.encode("ascii")

    log.info("Opening USB stick at %s …", PORT)
    s = Stick(PORT)
    s.connect()
    _stick_ref = s
    log.info("Stick connected")

    init_done = threading.Event()

    def _on_init():
        log.info("Stick initialised")
        init_done.set()

    s.initialize_stick(_on_init)
    init_done.wait(timeout=15)

    # ── Pairing mode ────────────────────────────────────────────────────────
    if PAIR_MODE:
        paired_mac = _do_pairing(s)
        if paired_mac:
            mac_str = paired_mac.upper()
            _mac_bytes = mac_str.encode("ascii")
            log.info("Using MAC %s going forward.", mac_str)
        else:
            log.error("Pairing failed — running in send-only mode with %s", mac_str)

    # ── Self-test ───────────────────────────────────────────────────────────
    # SELFTEST=1 physically cycles the relay OFF/ON/OFF once, straight through
    # the Plugwise stack — no MQTT, no planner. Use it to confirm the Circle+
    # actually switches (isolates hardware/pairing from the app logic).
    if os.environ.get("SELFTEST") == "1":
        global _last_relay_state
        log.info("SELFTEST: cycling relay OFF -> ON -> OFF (watch the lamp)")
        for st in (False, True, False):
            try:
                _switch(st)
            except Exception as e:
                log.error("SELFTEST switch failed: %s", e)
            time.sleep(2)
        _last_relay_state = "off"
        log.info("SELFTEST done.")

    # ── Command loop ────────────────────────────────────────────────────────
    log.info("Bridge live on %s  (Circle %s)", CMD_TOPIC, mac_str)
    log.info("If bulb doesn't respond, run:  PAIR=1 python3 plugwise_bridge.py")

    while True:
        try:
            cmd = _cmd_q.get(timeout=1.0)
        except queue.Empty:
            continue

        try:
            _switch(cmd == "on")
        except Exception as e:
            log.error("Switch failed: %s", e)


if __name__ == "__main__":
    t = threading.Thread(target=_mqtt_thread, daemon=True)
    t.start()
    log.info("MQTT thread started  (broker %s:%s)", MQTT_HOST, MQTT_PORT)

    try:
        _main()
    except KeyboardInterrupt:
        log.info("Stopped")
    except Exception as e:
        log.exception("Fatal: %s", e)
