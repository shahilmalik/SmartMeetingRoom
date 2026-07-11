from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("overview/", views.overview),
    path("sensors/", views.sensors),
    path("state/", views.state),
    path("plan/", views.plan),
    path("events/", views.events),
    path("commands/relay/", views.relay_command),
    path("commands/led/", views.led_command),
    path("commands/simulated/", views.simulated_command),
    path("commands/manual-override/", views.manual_override),
]
