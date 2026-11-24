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

## Set up a new Pi (the duck's Pi Zero 2 W)

Every step, as done on 2026-11-23. Each command that needs the Pi's password is run by you in your own terminal.

1. **Flash the card** with Raspberry Pi Imager on the PC: device *Raspberry Pi Zero 2 W*, OS *Raspberry Pi OS Lite (64-bit)*. In its settings: a hostname, a username and password, your Wi-Fi (2.4 GHz: the Zero 2 W has no 5 GHz), and *Enable SSH*. Paste the public key there (*Allow public-key authentication only*) to skip step 3.
2. **Find it on the network:** Windows often can't resolve `<hostname>.local`, so look for it in the router's client list, or `arp -a` after it has booted (about a minute).
3. **The SSH key**, once per PC: `ssh-keygen -t ed25519 -f ~/.ssh/duck_ed25519 -C duck-pi`, then put it on the Pi (asks for the password):
   ```powershell
   type $env:USERPROFILE\.ssh\duck_ed25519.pub | ssh USER@ADDRESS "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
   ```
4. **Copy the code and set up**, from the repo root in Git Bash: `bash pi/deploy.sh USER@ADDRESS --setup`. It copies `pi/` to `~/duck`, then runs `setup_pi.sh` there (asks for the password once): I2C at 400 kHz, Bluetooth unblocked with the Xbox controller's settings, the venv with onnxruntime and the IMU library. Then `sudo reboot`. Later code changes: `bash pi/deploy.sh USER@ADDRESS` alone.
5. **The Xbox controller:** `ssh -t -i ~/.ssh/duck_ed25519 USER@ADDRESS "sudo bash ~/duck/xbox_pair.sh"`, holding its pair button when asked ([TROUBLESHOOTING.md](../docs/dynamixel/TROUBLESHOOTING.md), The Pi and the gamepad).
6. **Check, with the duck powered** (nothing moves): `ls /dev/ttyACM*` (the bus board), `.venv/bin/python -m duck.set_id --scan` (all 15 servos), `/usr/sbin/i2cdetect -y 1` (the IMU at 0x4a or 0x4b), `.venv/bin/python run_policy.py --imu-check` (its gravity while you tilt the duck: nose down +x, left side down +y), `.venv/bin/python run_policy.py --pad-check` (the controller).
   **The IMU's axes:** `.venv/bin/python imu_axis_check.py --write`, the duck sitting with its torso upright. It holds every joint where it is (nothing moves, so the duck tips as one piece), and in 40 s you keep it still 3 s, tip it beak down about 20 deg and hold, back up, then onto its own left side and hold, back up. It writes `imu_to_robot` to the config (copy that back to the repo). On the first duck the board turned out mounted 90 deg round: forward is the sensor's -y.
7. **Shutting down:** `sudo shutdown -h now`, and unplug when the green LED stops. Losing power without it is usually harmless (ext4's journal), but can corrupt the card over many cuts: once the setup is settled, the overlay filesystem (`sudo raspi-config nonint do_overlayfs 0`, a reboot) makes the card read-only, and power cuts can't harm it. Not done yet.

## Set up the Pi, or a PC

One venv for every machine, `pi/.venv`, and nothing in the system Python. On the Pi (Raspberry Pi OS Lite, 64-bit, `pi/` copied to `/home/pi/duck`) `bash setup.sh` runs `setup_pi.sh`: I2C, Bluetooth, and every package (`setup_pi.sh --uart` for the bus board on the Pi's UART instead of USB). For an Xbox Series controller, then `sudo bash xbox_pair.sh`: it pairs it past the Pi's Bluetooth connect-drop loop ([TROUBLESHOOTING.md](../docs/dynamixel/TROUBLESHOOTING.md), The Pi and the gamepad). On a PC (Windows in Git Bash, Linux, macOS), everything, from the repo root:

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

**With the bus on the duck's Pi**, the Pi sends its readings over Wi-Fi and the PC draws them. On the Pi, read only (nothing moves): `.venv/bin/python telemetry.py` (all 15 servos and the IMU, 30 times a second, on port 9100). While the Pi drives the duck, `run_policy.py --telemetry` sends the same instead: only one program can own the bus, so stop `telemetry.py` first (`pkill -f "[t]elemetry.py"`). On the PC: `python twin.py --remote duck.local` (the Pi's address), which also prints the IMU's gravity every 2 s. With the IMU in the stream, the twin leans the body as the IMU measures, not by assuming the soles are flat: sitting folded, the duck rests on its heels, and the feet-flat guess tipped the body 12 deg forward (`--feet-flat` brings it back).

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

## Drive it from the Xbox controller

`run_policy.py --pad` runs a walk policy (by default `models/walk_style.onnx`, which needs the IMU) from an Xbox Series controller paired to the Pi (`sudo bash xbox_pair.sh`). The duck waits, sitting, torque on, for:

| Control | Does |
|---|---|
| A | stand up (the scripted rise), then the policy takes over |
| left stick | walk: up/down forward and back (`--vx-max`, 0.12 m/s), left/right sideways (`--vy-max`, 0.08) |
| RT, held | faster forward, up to `--vx-boost` (0.2 m/s) |
| right stick, left/right | turn (`--wz-max`, 0.8 rad/s) |
| d-pad | the head: up/down pitch, left/right turn (`--head-max`, 0.3 rad) |
| X | a nod |
| Y | beak open / shut |
| B | sit down (the scripted lower), then wait for A again |
| Menu, sitting | quit |
| LB + RB | stop: eases down at once, torque off, quit |

The walk command changes at most `--accel` (0.4 m/s per s), so a stick flicked to full doesn't jerk the legs. If the controller drops while standing for `--pad-lost` (1 s), it sits down. Every other stop is as for the scripted runs (a hardware error, a low supply, the body tipped past `--max-tilt`). `python run_policy.py --pad-check` prints the commands the controller gives, with no servos, and `python -m duck.gamepad` prints its raw sticks and buttons.

In the simulator, a scripted controller stands in: `--pad '0:A;4:ly=1;11:ly=0;13:rx=1;17:rx=0;18:X;30:B;36:Menu'` (seconds:what, see `duck/gamepad.py`), with `--rise 0 --blend 0.3`, as the simulated duck starts upright and off balance, not sitting.

### The controller launcher (nothing to type)

`launcher.py` runs on the Pi from boot, as the `duck-launcher` service (`sudo bash install_launcher.sh`, which `setup_pi.sh` runs). Idle, it holds no servo. **B** starts the head mode below, and B inside it turns it off again. With `--allow-walk` at install, **Menu + A** starts `run_policy.py --pad` (then A stands, B sits): off for now, until the Pi's power holds under load. A script run by hand that needs the bus (`stand_test.py`, `telemetry.py`) needs `sudo systemctl stop duck-launcher` first, and `start` after. Logs: `journalctl -u duck-launcher -f`.

### The head alone, sitting

`python head_pad.py` moves only the neck, head and beak from the controller, no policy. The legs hold the sitting pose they're in (torque on, goal where each is: nothing moves; `--legs-limp` leaves them off). Right stick: head pitch (up tips the face forward) and turn; d-pad: neck (up tips it back) and roll; X a nod, Y the beak, A back to the start, B or Menu back to the start then torque off. A held stick keeps the joint moving (`--speed`, 0.8 rad/s); let go and it stays. Each joint is kept inside its limits, widened to where it starts. Stop it with B, not by killing it: a killed run leaves every servo holding its last goal, torque on.

## Record a motion by hand, play it back

`motion.py` records a motion while you move the duck by hand, every servo limp, and plays it back on the servos:

```bash
python motion.py record wave --countdown 5 --view
```

```bash
python motion.py play wave --speed 0.5 --view
```

Recording reads all 15 joints 25 times a second after a 5 s countdown, with the twin window following, till Ctrl-C (in the terminal, not the window). It saves `motions/<name>.json` and says which joints moved, and how far the end is from the start.

Playback eases from where the duck is into the first recorded pose, plays it, and eases back to where it started before the torque goes off. It refuses a recording that ends more than 20 degrees from where it began, on any joint (`--max-loop`), and won't start unless the duck is within 15 degrees of the first pose (`--max-start`): move those joints and try again. `--preview` plays it on the model only. The legs are stiff (gain 1500), the neck too (1200, it lifts the whole head), and the head and beak softer and damped (600, D 300: stiffer, the head yaw hunts). The safety is stand_test.py's: current caps, and a stop eases the duck back before letting go. Nothing balances it: if a hand steadied it while recording, steady it while it plays.

**Try the sample:** `motions/head_look_around.json`, 20.6 s. The head starts folded down in front, swings up and over to lean back, looks to one side, and comes back down; the legs barely move.

In the simulator, no duck needed (`bash setup.sh --sim` first):

```bash
python motion.py play head_look_around --preview
```

On the real duck: put it in the start pose the preview shows, steady it, and:

```bash
python motion.py play head_look_around --speed 0.5 --view --min-volts 4.2
```

At half speed the neck lifts the head at about 33 degrees a second, drawing about 475 mA, near its 600 mA cap; on a 5 V bench supply the voltage sags, hence `--min-volts 4.2` (the XL330 is rated to 3.7 V). With a 6 V UBEC it shouldn't need it.

## What the policy sees

61 numbers at 50 Hz, in this order: angular velocity 3, gravity 3, joint positions minus home 14, joint velocities 14, last action 14, twist command 3, head command 4, body command 6. It returns 14 joint targets, as offsets from home. See `duck/policy.py`. A policy trained with foot switches has 63 inputs and is refused.

The loop stops the policy if the body tips past its limit, the battery falls under 6.6 V or a servo stops answering, and it turns the torque off on the way out.

Regenerate the config and the simulator's model after a design change:

```bash
MILLI_RECIPE=dynamixel python tools/make_pi_config.py
```
