# The duck's Pi code

Runs on the Raspberry Pi Zero 2 W in the head: reads 15 XL330 servos and the BNO085, runs a policy at 50 Hz, and writes the servos' targets.

**For the all-Dynamixel duck only.** The HD-1910 and all-Feetech ducks need Feetech's bus protocol, and the hybrid needs two buses.

**Status:** tested only against the simulator below. It has never run on a real Pi or real servos. There's no trained policy for this design yet, so `hold` and `wave` are stand-ins: `hold` sags and sits down, and neither walks.

## Try it in simulation

No Pi and no GPU needed. The simulator speaks the real Dynamixel bytes on a socket and answers as the IMU, so the Pi's code runs unchanged:

```bash
pip install -r pi/requirements.txt mujoco
```

```bash
cd pi && python sim/test_sim.py
```

To drive it yourself, run the simulator in one terminal:

```bash
cd pi && python sim/server.py --pinned
```

and the Pi's code in another:

```bash
cd pi && python run.py --port socket://127.0.0.1:9000 --imu 127.0.0.1:9001 --policy wave --no-fall
```

`--pinned` holds the body in the air. Leave it off to stand on the floor. A trained policy goes in the same way: `--policy models/walk.onnx --vx 0.2`.

**What this doesn't tell you:** the Pi Zero's own speed. On a PC a tick takes about 2 ms of the 20 ms budget, with a stand-in network that's far smaller than a real policy. Time a real policy on the Pi itself: `run.py` prints the ticks that ran late.

## Set up the Pi, or a PC

One venv for every machine, `pi/.venv`, and nothing in the system Python. On the Pi (Raspberry Pi OS Lite, 64-bit, `pi/` copied to `/home/pi/duck`) `bash setup.sh` runs `setup_pi.sh`: the UART, I2C, Bluetooth, and every package. On a PC (Windows in Git Bash, Linux, macOS), everything, from the repo root:

```bash
bash setup.sh
```

or in `pi/`, only what you need: `bash setup.sh` the servo tools (`requirements-pc.txt`), `--sim` the simulator, the policy runtime and the digital twin (`requirements-sim.txt`), `--tools` the design tools (`../requirements-tools.txt`). MuJoCo is pinned to the version the sim model is built with.

Then run the code with the venv's Python: `.venv/bin/python` on the Pi and Linux, `.venv/Scripts/python.exe` on Windows.

## First run on the robot

Lift the duck on a stand, away from its joint limits, before any of this. Nothing has been tried on real servos.

1. **Set each servo's id and speed, one servo at a time,** before any are chained: a new XL330 is id 1 at 57600, so two together answer over each other. From a PC, through the Waveshare board's USB-C with its jumpers at B and 5 V on its terminals (the port is found by itself), or from the Pi with them at A and `--port /dev/serial0`. After `bash setup.sh`:

```bash
python -m duck.set_id --all
```

It goes right leg, left leg, neck, head, each from the bottom up, asking for one servo at a time. It writes the id from the table below and 1 Mbps, then turns the horn a little each way: label the servo. It refuses past 6 V, the XL330's maximum. `--start left_ankle` carries on from a joint, `--find` shows the servo plugged in without changing it, and `--scan` lists every servo on a chain, with any missing. Each servo is reset to factory settings, keeping its new id and 1 Mbps (many arrive set up for another robot), and what it is and how it tested go into `config/servos.json`, by id: model, firmware, the settings it came with, its middle position as set by hand, the nudge, and any range or load test. `--nudge ID` repeats only the nudge, 10 degrees or less inside the joint's limits, and changes no setting. No big moves: a servo is never sent to mid-range. ROBOTIS's Dynamixel Wizard does the same by hand.

All 15 were set and checked on one bus on 2026-11-21: see `config/servos.json` and [docs/dynamixel/TROUBLESHOOTING.md](../docs/dynamixel/TROUBLESHOOTING.md). The two hip yaws have their middles at the servo's 0/4095 wrap: refit their horns near 2048 before they're driven. Plug the board's USB in before its 5 V: problems so far are in [docs/dynamixel/TROUBLESHOOTING.md](../docs/dynamixel/TROUBLESHOOTING.md).
2. **Measure the centres,** with the duck posed at zero by hand: legs straight, head level, beak shut:

```bash
python -m duck.calibrate --port /dev/serial0
```

3. **Check the directions on the stand.** Every joint starts at `direction: 1` in `config/dynamixel.json`, and some will be wrong. Flip those that move the wrong way:

```bash
python run.py --policy wave --no-fall --seconds 20
```

4. **Check the IMU.** Gravity should read about (0, 0, -1) with the body level. If it doesn't, fix `imu_to_robot` in the config.

| Servo ids | Joints |
|---|---|
| 1-5 | right ankle, knee, hip pitch, hip roll, hip yaw |
| 6-10 | left ankle, knee, hip pitch, hip roll, hip yaw |
| 11-15 | neck pitch, head pitch, head yaw, head roll, beak |

## The digital twin

The real duck's pose on the MuJoCo model, live, in its true colours, standing on the floor. Read only: it never writes to a servo.

```bash
python twin.py
```

`--snapshot pose.png` saves front, side and three-quarter views. Calibrate first (`python -m duck.calibrate`, the duck at zero; `--joints neck_pitch,head_pitch` does a few), then move one joint at a time and check the model turns the same way: flip a joint's `direction` in the config where it doesn't.

## Powered tests: standing up

`stand_test.py` drives the real duck from where it is (sitting) to standing and back, the joints in current-limited position mode. It's scripted joint angles: no balance, no IMU, so someone steadies the duck. The run in the [main README](../README.md) was:

```bash
python stand_test.py --show --keep-head --face-forward --neck-offset -10 --gain 1500 --rise 12 --lower 12 --view
```

- `--show`: at standing, the head turns side to side, nods a little, slowly, and the beak opens and shuts. Big or fast moves front to back tip the duck.
- `--keep-head`: the neck and head hold the pose they're set in by hand at the start; `--neck-offset` nudges the neck (negative is more upright, the weight forward). `--stand-pose poses/stand_balanced.json` stands in a whole pose found by hand (`python twin.py --save-pose`).
- `--face-forward`: the head pitch follows the body through the rise and the lower, so the face stays straight ahead.
- `--gain 1500`: at the factory 400, or 800, the knees trail 12 degrees under the duck's weight.
- `--view`: a MuJoCo window shows the joint angles the servos measure, live; `--wait-for FILE` holds there, torque off, till the file appears, then counts down 5 s.
- `--preview`: the same routine in the window, no servos.
- Safety: each servo's current is capped (legs 800 mA, head 600, beak 300), and a stop (a servo error, the supply under 4.6 V, a joint 15 degrees behind) eases the duck back down to sitting before the torque goes off. Every tick is logged to `stand_test_log.csv`.

`sim/server.py --view --start pose.json --kp 4 --peak-nm 0.28` runs the simulator with a window, from a saved pose, with the servo stiffness and torque of the test's settings (5 V, 800 mA). Unsupported, the simulated duck falls from a crouch, as the real one would.

## What the policy sees

61 numbers at 50 Hz, in this order: angular velocity 3, gravity 3, joint positions minus home 14, joint velocities 14, last action 14, twist command 3, head command 4, body command 6. It returns 14 joint targets, as offsets from home. See `duck/policy.py`. A policy trained with foot switches has 63 inputs and is refused.

The loop stops the policy if the body tips past its limit, the battery falls under 6.6 V or a servo stops answering, and it turns the torque off on the way out.

Regenerate the config and the simulator's model after a design change:

```bash
MILLI_RECIPE=dynamixel python tools/make_pi_config.py
```
