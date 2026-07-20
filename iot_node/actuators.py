from . import hardware


class Actuators:
    def __init__(self):
        self.relay_state = 0
        self.led_brightness = 0
        self.buzzer_state = 0

    def set_relay(self, on):
        """Logical fan/heater — there is no physical relay wired. We keep the
        state (for the CO2/temperature model and the dashboard) but never drive
        a GPIO pin, since D5 now carries the buzzer."""
        value = 1 if on else 0
        hardware.write_fan(value)
        self.relay_state = value
        return self.relay_state

    def set_led(self, brightness):
        value = int(max(0, min(255, brightness)))
        hardware.write_analog(hardware.LED_PORT, value)
        self.led_brightness = value
        return self.led_brightness

    def set_buzzer(self, on):
        value = 1 if on else 0
        hardware.write_digital(hardware.BUZZER_PORT, value)
        self.buzzer_state = value
        return self.buzzer_state

    def apply_command(self, actuator_id, payload):
        if actuator_id == "relay":
            state = payload.get("state")
            if state is None:
                state = payload.get("value")
            on = str(state).lower() in ("1", "on", "true", "open")
            return {"relay": self.set_relay(on)}
        # The LED and buzzer are driven by the indicator loop (noise / health),
        # so their MQTT commands only carry the indicator MODE, handled in
        # iot_node — nothing to write directly here.
        return {}

    def snapshot(self):
        return {
            "relay": self.relay_state,
            "led": self.led_brightness,
            "buzzer": self.buzzer_state,
        }
