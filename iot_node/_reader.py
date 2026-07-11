import json
import sys
import os

sys.path.insert(0, '/home/shahilmalik')

CALL = sys.argv[1] if len(sys.argv) > 1 else ""

try:
    import grovepi as gp
    if CALL == "analog0":
        print(json.dumps(gp.analogRead(0)))
    elif CALL == "analog1":
        print(json.dumps(gp.analogRead(1)))
    elif CALL == "button":
        print(json.dumps(gp.digitalRead(8)))
    elif CALL == "ultrasonic":
        print(json.dumps(gp.ultrasonicRead(7)))
    elif CALL == "dht":
        result = gp.dht(4, 0)
        print(json.dumps(result))
    else:
        print(json.dumps(None))
except Exception as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
