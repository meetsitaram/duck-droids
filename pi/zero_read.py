"""The ten leg joints' angles, by the config's centres, once a second for 90 s: for checking a calibration (each leg flat, each foot flat
should read near 0). No torque. Stop the launcher first, it holds the bus: systemctl --user stop duck-launcher; python zero_read.py
"""
import json, time
from duck import dxl
from duck.set_id import find_port
c = json.load(open("config/dynamixel.json"))["joints"]
b = dxl.Bus(find_port(), timeout=0.05)
K = 360 / 4096
legs = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
        "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]
ids = [c[n]["id"] for n in legs]
t0 = time.time()
while time.time() - t0 < 90:
    r = b.sync_read(ids, 132, 4)
    s = []
    for n in legs:
        j = c[n]
        p = int.from_bytes(r[j["id"]], "little", signed=True)
        d = ((p - j["centre"] + 2048) % 4096 - 2048) * K * j["direction"]
        s.append(f"{n.replace('left_', 'L').replace('right_', 'R')} {d:+5.1f}")
    print(f"{time.time() - t0:4.0f}s " + "  ".join(s), flush=True)
    time.sleep(1)
