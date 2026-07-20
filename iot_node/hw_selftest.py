"""Standalone GrovePi actuator test — run DIRECTLY on the Pi.

    python3 iot_node/hw_selftest.py

No MQTT, no threads, no bus lock, no simulation — just talks to grovepi and
tells you exactly which physical output responds. This isolates *hardware +
grovepi writes* from the rest of the system. Ctrl-C to stop.

If a step does nothing on the board, that pin/module/grovepi-write is the
problem (not the app). If everything here works but the live app doesn't,
the problem is in the app (threading / bus contention), not the wiring.
"""
import sys
import time

# Same path the rest of the node uses to find the patched grovepi.
sys.path.insert(0, "/home/shahilmalik")
import grovepi  # noqa: E402

LED = 3       # D3  (status / noise LED, PWM-capable)
BUZZER = 5    # D5  (health-alarm buzzer)
BUTTON = 8    # D8  (room-light switch)


def banner(msg):
    print(f"\n=== {msg} ===", flush=True)


def main():
    print("grovepi module:", getattr(grovepi, "__file__", "?"), flush=True)
    grovepi.pinMode(LED, "OUTPUT")
    grovepi.pinMode(BUZZER, "OUTPUT")
    grovepi.pinMode(BUTTON, "INPUT")
    print("pinMode done.", flush=True)

    banner("LED via analogWrite (PWM) — should be ON solid 2s")
    grovepi.analogWrite(LED, 255)
    time.sleep(2)
    grovepi.analogWrite(LED, 0)

    banner("LED via digitalWrite — should be ON solid 2s (fallback if PWM did nothing)")
    grovepi.digitalWrite(LED, 1)
    time.sleep(2)
    grovepi.digitalWrite(LED, 0)

    banner("LED blink 6x")
    for _ in range(6):
        grovepi.digitalWrite(LED, 1)
        time.sleep(0.25)
        grovepi.digitalWrite(LED, 0)
        time.sleep(0.25)

    banner("Buzzer ON 1s — should sound")
    grovepi.digitalWrite(BUZZER, 1)
    time.sleep(1)
    grovepi.digitalWrite(BUZZER, 0)

    banner("Buzzer beep 3x")
    for _ in range(3):
        grovepi.digitalWrite(BUZZER, 1)
        time.sleep(0.2)
        grovepi.digitalWrite(BUZZER, 0)
        time.sleep(0.3)

    banner("Button read for 6s — press it, values should change 0<->1")
    t0 = time.time()
    while time.time() - t0 < 6:
        print("   button =", grovepi.digitalRead(BUTTON), flush=True)
        time.sleep(0.4)

    print("\nDone. Note which steps physically responded.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
    except Exception as e:
        print(f"\nERROR: {e}", flush=True)
        raise
