"""Make the buzzer sound — run DIRECTLY ON THE PI, nothing else running.

    sudo systemctl stop iot-node          # free the bus first
    python3 iot_node/buzz.py              # drive D5 every which way
    python3 iot_node/buzz.py scan         # find which port the buzzer is on
    python3 iot_node/buzz.py 6            # drive a specific port (e.g. D6)

Prints diagnostics and try/catches every method so we learn exactly what the
hardware does. If NOTHING here makes a sound, it's the port/wiring/buzzer type,
not the app.
"""
import sys
import time

sys.path.insert(0, "/home/shahilmalik")
import grovepi  # noqa: E402


def diag():
    print("grovepi module:", getattr(grovepi, "__file__", "?"), flush=True)
    try:
        print("firmware version:", grovepi.version(), flush=True)
    except Exception as e:
        print("version() failed:", e, flush=True)


def step(desc, fn):
    print(f"\n>>> {desc}", flush=True)
    try:
        fn()
        print("    sent OK", flush=True)
    except Exception as e:
        print("    ERROR:", e, flush=True)


def drive(port):
    def digital_high():
        grovepi.pinMode(port, "OUTPUT")
        grovepi.digitalWrite(port, 1)
        time.sleep(2)
        grovepi.digitalWrite(port, 0)

    def beeps():
        grovepi.pinMode(port, "OUTPUT")
        for _ in range(4):
            grovepi.digitalWrite(port, 1)
            time.sleep(0.25)
            grovepi.digitalWrite(port, 0)
            time.sleep(0.25)

    def toggle_fast():
        grovepi.pinMode(port, "OUTPUT")
        t0 = time.time()
        while time.time() - t0 < 1.5:
            grovepi.digitalWrite(port, 1)
            grovepi.digitalWrite(port, 0)

    def pwm():
        grovepi.pinMode(port, "OUTPUT")
        for v in (80, 160, 255):
            grovepi.analogWrite(port, v)
            time.sleep(0.4)
        grovepi.analogWrite(port, 0)

    step(f"D{port}: digitalWrite HIGH 2s  (Grove ACTIVE buzzer -> should sound)", digital_high)
    step(f"D{port}: 4 beeps", beeps)
    step(f"D{port}: fast toggle 1.5s  (helps a passive buzzer)", toggle_fast)
    step(f"D{port}: analogWrite PWM 80->255  (PWM buzzer / LED)", pwm)


def scan():
    print("\nSCAN: buzzing each digital port 1.5s. Note which one you HEAR.\n", flush=True)
    for port in (2, 3, 4, 5, 6, 7, 8):
        print(f">>> now driving D{port} ...", flush=True)
        try:
            grovepi.pinMode(port, "OUTPUT")
            grovepi.digitalWrite(port, 1)
            time.sleep(1.5)
            grovepi.digitalWrite(port, 0)
        except Exception as e:
            print("    ERROR:", e, flush=True)
        time.sleep(0.6)


def main():
    diag()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "scan":
        scan()
    else:
        port = int(arg) if arg.isdigit() else 5
        drive(port)
    print("\nDone. Which step/port made a sound?", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
    except Exception as e:
        print("\nFATAL:", e)
        raise
