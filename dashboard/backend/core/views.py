import sys
import time

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from shared import mqtt_topics as topics

from .mqtt_client import store
from .serializers import (
    ActuatorTestSerializer,
    LedCommandSerializer,
    ManualOverrideSerializer,
    RelayCommandSerializer,
    SensorOverrideSerializer,
    SimulatedCommandSerializer,
)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "mqtt_connected": store.connected, "ts": time.time()})


@api_view(["GET"])
def overview(request):
    return Response(store.snapshot())


@api_view(["GET"])
def sensors(request):
    snapshot = store.snapshot()
    return Response({"sensors": snapshot["sensors"], "ts": time.time()})


@api_view(["GET"])
def state(request):
    return Response(store.snapshot()["state"])


@api_view(["GET"])
def plan(request):
    return Response(store.snapshot()["plan"])


@api_view(["GET"])
def events(request):
    return Response({"events": store.snapshot()["events"]})


@api_view(["POST"])
def relay_command(request):
    serializer = RelayCommandSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ok = store.publish(topics.actuator_cmd_topic(topics.ACTUATOR_RELAY), serializer.validated_data)
    return _ack(ok, serializer.validated_data)


@api_view(["POST"])
def led_command(request):
    serializer = LedCommandSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ok = store.publish(topics.actuator_cmd_topic(topics.ACTUATOR_LED), serializer.validated_data)
    return _ack(ok, serializer.validated_data)


@api_view(["POST"])
def test_command(request):
    serializer = ActuatorTestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = {"ts": time.time(), **serializer.validated_data}
    ok = store.publish(topics.actuator_cmd_topic("test"), payload)
    return _ack(ok, payload)


@api_view(["POST"])
def simulated_command(request):
    serializer = SimulatedCommandSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    actuator = serializer.validated_data["actuator"]
    ok = store.publish(topics.actuator_cmd_topic(actuator), serializer.validated_data)
    return _ack(ok, serializer.validated_data)


@api_view(["POST"])
def sensor_override(request):
    serializer = SensorOverrideSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = {"ts": time.time(), "values": serializer.validated_data["values"]}
    ok = store.publish(topics.OVERRIDE_SENSORS, payload, retain=True)
    return _ack(ok, payload)


@api_view(["POST"])
def manual_override(request):
    serializer = ManualOverrideSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = {"source": "dashboard", "ts": time.time(), **serializer.validated_data}
    ok = store.publish(topics.EVENT_MANUAL, payload)
    return _ack(ok, payload)


def _ack(ok, payload):
    if not ok:
        return Response(
            {"published": False, "detail": "MQTT client not connected"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"published": True, "payload": payload}, status=status.HTTP_202_ACCEPTED)
