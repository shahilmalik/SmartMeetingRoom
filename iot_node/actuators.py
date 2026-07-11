from . import hardware


class Actuators:
    def __init__(self):
        self.relay_state = 0
        self.led_brightness = 0

    def set_relay(self, on):
        value = 1 if on else 0
        hardware.write_digital(hardware.RELAY_PORT, value)
        self.relay_state = value
        return self.relay_state

    def set_led(self, brightness):
        value = int(max(0, min(255, brightness)))
        hardware.write_analog(hardware.LED_PORT, value)
        self.led_brightness = value
        return self.led_brightness

    def apply_command(self, actuator_id, payload):
        if actuator_id == "relay":
            state = payload.get("state")
            if state is None:
                state = payload.get("value")
            on = str(state).lower() in ("1", "on", "true", "open")
            return {"relay": self.set_relay(on)}
        if actuator_id == "led":
            brightness = payload.get("brightness")
            if brightness is None:
                brightness = payload.get("value", 0)
            return {"led": self.set_led(brightness)}
        return {}

    def snapshot(self):
        return {"relay": self.relay_state, "led": self.led_brightness}
