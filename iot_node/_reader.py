import json
import statistics
import sys
import os
import time

sys.path.insert(0, '/home/shahilmalik')

CALL = sys.argv[1] if len(sys.argv) > 1 else ""

# Grove ports (kept in sync with hardware.py).
LED_PORT = 3
BUZZER_PORT = int(os.environ.get("BUZZER_PORT", "5"))
BUTTON_PORT = 8

try:
    import grovepi as gp
    if CALL == "analog0":
        print(json.dumps(gp.analogRead(0)))
    elif CALL == "analog1":
        print(json.dumps(gp.analogRead(1)))
    elif CALL == "button":
        print(json.dumps(gp.digitalRead(BUTTON_PORT)))
    elif CALL == "ultrasonic":
        # Median of a few quick samples so one spurious echo can't move the
        # reading — the app's occupancy logic then stays stable.
        vals = []
        for _ in range(5):
            try:
                d = gp.ultrasonicRead(7)
                if isinstance(d, (int, float)) and d > 0:
                    vals.append(d)
            except Exception:
                pass
            time.sleep(0.04)
        print(json.dumps(int(statistics.median(vals)) if vals else None))
    elif CALL == "dht":
        result = gp.dht(4, 0)
        print(json.dumps(result))
    elif CALL == "setup":
        # Configure the indicator/input pins. Done in a fresh subprocess so the
        # software-I2C bus is freshly initialised, same as every read/write.
        gp.pinMode(LED_PORT, "OUTPUT")
        gp.pinMode(BUZZER_PORT, "OUTPUT")
        gp.pinMode(BUTTON_PORT, "INPUT")
        print(json.dumps(True))
    elif CALL.startswith("awrite:"):
        _, port, val = CALL.split(":")
        p = int(port)
        # Set OUTPUT in THIS subprocess right before writing — pinMode from a
        # previous, already-exited subprocess can't be relied on.
        gp.pinMode(p, "OUTPUT")
        gp.analogWrite(p, int(val))
        print(json.dumps(True))
    elif CALL.startswith("dwrite:"):
        _, port, val = CALL.split(":")
        p = int(port)
        gp.pinMode(p, "OUTPUT")
        gp.digitalWrite(p, int(val))
        print(json.dumps(True))
    else:
        print(json.dumps(None))
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
