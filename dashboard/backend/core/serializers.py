from rest_framework import serializers


class RelayCommandSerializer(serializers.Serializer):
    state = serializers.CharField()


class LedCommandSerializer(serializers.Serializer):
    brightness = serializers.IntegerField(min_value=0, max_value=255)


class ActuatorTestSerializer(serializers.Serializer):
    # Momentary hardware test: force one indicator on for `duration` seconds.
    target = serializers.ChoiceField(choices=["led", "buzzer"])
    duration = serializers.FloatField(required=False, min_value=0.2, max_value=10.0, default=2.0)


class ManualOverrideSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="dashboard")


class SimulatedCommandSerializer(serializers.Serializer):
    actuator = serializers.ChoiceField(choices=["ac", "blinds", "socket"])
    state = serializers.CharField(required=False)
    position = serializers.IntegerField(required=False, min_value=0, max_value=100)


class SensorOverrideSerializer(serializers.Serializer):
    # Full map of currently-held sensor values ({sensor_id: value}); an empty
    # map releases every hold and returns all sensors to live readings.
    values = serializers.DictField(required=False, default=dict)


class GoalSerializer(serializers.Serializer):
    goal = serializers.ChoiceField(choices=["comfort", "energy-saving", "auto"])
