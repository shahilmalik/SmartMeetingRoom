from rest_framework import serializers


class RelayCommandSerializer(serializers.Serializer):
    state = serializers.CharField()


class LedCommandSerializer(serializers.Serializer):
    brightness = serializers.IntegerField(min_value=0, max_value=255)


class ManualOverrideSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="dashboard")


class SimulatedCommandSerializer(serializers.Serializer):
    actuator = serializers.ChoiceField(choices=["ac", "blinds", "socket"])
    state = serializers.CharField(required=False)
    position = serializers.IntegerField(required=False, min_value=0, max_value=100)


class GoalSerializer(serializers.Serializer):
    goal = serializers.ChoiceField(choices=["comfort", "energy-saving", "auto"])
