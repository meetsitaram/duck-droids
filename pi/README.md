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

**Watch the duck from any PC on its Wi-Fi:** `python watch.py <address> --user <user>` (the repo's Python, `pi/.venv`) opens the live twin and prints the duck's launcher log over SSH, together, until Ctrl-C. The twin draws whatever mode is running (each sends its servo positions and IMU on port 9100) and reconnects by itself when the next one starts; `--no-log` needs no SSH, `--no-twin` gives the log alone. Set `DUCK_USER` and `DUCK_KEY` to skip the options.

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

### Calibrating the zeros (calibrate.py)

`python calibrate.py` (launcher stopped) goes joint by joint, ankles up to the head: every other servo holds where it is and only the one being calibrated goes limp. Put it at its zero by a reference, not by eye (knee: thigh and shin flat on the table together, as the knee bends both ways and has no stop at straight; ankle: foot flat, shin upright; hip roll: square to the servo it hangs from; hip pitch: straight down from the side; hip yaw: foot straight ahead), then **A** on the controller sets that as its zero, **B** keeps the old one; it buzzes for each. A change over 20 deg needs A twice. Each centre is written to `config/dynamixel.json` as soon as it's set (the old one kept as `.bak`): copy it back to the repo. The twin (`twin.py --remote <pi>`) shows it: the joint being calibrated pulsing yellow with what to do and its angle on screen, done joints green, the rest grey. `python calibrate.py right_knee left_knee` only those; `--done ...` shows joints already done green. By hand the zeros are good to a few degrees, no better.

2026-11-24: the right knee was 12 deg off (it stood 12 deg more bent than told, the duck leaning right), the hips 3-6 deg; the ankles and the left knee were right.

`servo_wiggle.py 1 6 2 7` turns one servo at a time (by ID) a little and back, the rest limp: which joint is which, against the twin. `leg_sweep.py` curls the knees and ankles in, straight, and in again, held in the air, printing where each got to.

### Which servo is weak? (motor_test.py)

`python motor_test.py` (launcher stopped: `systemctl --user stop duck-launcher`) needs no policy: a slow rise to the standing pose (hold the duck), then each servo in turn gets a quick kick, 8 deg forward and back (head 10 deg), while the rest hold. Per kick: the delay before the joint moves, the time to half and 90 % of the way, overshoot, how far short it ends, peak current, the servo's own lowest voltage, and every servo's voltage mid-kick (where the power chain sags). It ends with a summary flagging the slow or short joints, and writes `motor_test.json` and `motor_test.csv`. Run it twice: **held up in the air** (feet off the floor: the motor alone) and **standing, held** (under load). Compare with the simulator's own numbers for the same two cases, in `motor_test_sim/` (`in_air.json`: every joint at 90 % in 62-94 ms, ending within 0.1 deg; `standing_held.json`: there the knees and hip rolls end 2-6 deg short even in the simulator, as the floor and the hand lock the leg). `--only legs`, `--amp 6`. `--stress 10 --no-kicks`: every servo steps at once, + then -, the worst load on the supply: total current, each servo's voltage, and the resistance between the supply and the servos from the sag (`motor_stress.csv`). It streams the servos and the IMU to the twin. `--no-kicks --settle 60` is the stand-still IMU check: the IMU's pitch and roll over the hold are printed and written to `stand_tilt.csv` (the standing pose has the feet parallel to the body, so level is 0, 0). 2026-11-24, after the IMU fix: pitch +0.3, roll +0.3 deg over 60 s, standing alone. While standing it sends the goal pose and each joint's current: the twin draws the goal as a see-through blue duck, each leg and head joint green on its goal or red past 1.5 deg (listed with its mA), and the IMU's pitch and roll beside the expected. `--tune JOINT`: standing, the d-pad up/down nudges that joint 0.5 deg a press, A saves its zero there, B keeps the old one. 2026-11-24, lifted and set down 3 times while standing: lifted, every leg joint within 0.6 deg of its goal (the zeros hold); on the table the right knee sags 3.4 deg at 117 mA, the left 1.1 deg at 35 mA, the rest within 1 deg, the body 6 deg nose down and 1.7 deg right side down: the weight sits on the right knee, and its sag tips more weight onto it.

### Stand only (the stand policies)

`python run_policy.py --pad --stand-only --model models/stand_nod.onnx --rise 0 --blend 0` stands with the IMU policy trained to stand still while the head moves (2026-11-24, `milli_dynamixel_imu_stand_nod`). `--stand-only` never sends a walk command: the left stick does nothing, and the right stick (and the d-pad) move the head, X nods, Y the beak. RT + A held 1 s (A alone with `--stand-only` does nothing): the policy itself stands it up from sitting (no scripted rise: in the simulator the scripted rise from the real sitting pose tipped over, and the policy rose cleanly, steady in about 5 s). B: the scripted lower, as before. `--rise-model models/sitstand2.onnx` lets the sit/stand skill do the first `--rise-policy-s` (6) seconds instead; not needed so far.

Checked in the simulator, from the real duck's sitting pose (`sim/server.py --start poses/sit_real.json --start-level`, A at once, since that pose held still falls back in the sim, whose knee stops at 63° where the real one reaches 92°): it rises, stands with legs moving 0.1-0.2° and tilt under 2.3° while the head nods ±0.4 rad and turns ±0.5 rad. In mjlab, pushed every 3-6 s: 100 % stay up at 0.15 m/s, 86 % at 0.32 m/s. Renders: `docs/images/policies/dynamixel/stand_nod.mp4`, `stand_imu.mp4`.

### The controller launcher (nothing to type)

`launcher.py` runs on the Pi from boot, as the user service `duck-launcher` (`bash install_launcher_user.sh`, no sudo: `loginctl enable-linger` starts a user's services at boot; `setup_pi.sh` runs it). Idle, it holds no servo. Every combo is **held 1 s** (`--hold-s`), and the controller buzzes when it takes effect; a brush or a quick tap does nothing:

| Combo, held 1 s | Does |
|---|---|
| **RT + A** | stand: a scripted rise, then the stand policy trained on Pollen's XL330 model (`run_policy.py --pad --stand-only --auto-stand --bam`, `stand_bam.onnx`; before 2026-11-24 `stand_nod.onnx`). Right stick and d-pad: the head; X: a nod; Y: the beak; no walk command ever. **RT + A again:** it sits down and the mode ends |
| **RB + B** | head mode, sitting (`head_pad.py`, below). **RB + B again:** the head goes back to its start, torque off |
| **LT + A** | the walk policy, only with `--allow-walk` at install: off until the power holds under load |
| **LB + RB** | inside any mode: stop at once, torque off |

If the controller drops for 1 s while standing, it sits down. A script run by hand that needs the bus (`stand_test.py`, `telemetry.py`) needs `systemctl --user stop duck-launcher` first, and `start` after. Log: `tail -f ~/duck/launcher.log` (the user journal isn't kept on this Pi); each run's own CSV is `~/duck/run_policy_log.csv`. `install_launcher.sh` is the same as a system service, with sudo: use one or the other. The buzz is force feedback through the kernel's `hid-microsoft` driver (`duck/gamepad.py` `rumble()`).

### The head alone, sitting

`python head_pad.py` moves only the neck, head and beak from the controller, no policy. The legs hold the sitting pose they're in (torque on, goal where each is: nothing moves; `--legs-limp` leaves them off). Right stick: head pitch (up tips the face forward) and turn; d-pad: neck (up tips it back) and roll; X a nod, Y the beak, A back to the start, RB + B held 1 s back to the start then torque off. A held stick keeps the joint moving (`--speed`, 0.8 rad/s); let go and it stays. Each joint is kept inside its limits, widened to where it starts. Stop it with B, not by killing it: a killed run leaves every servo holding its last goal, torque on.

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

**Retargeted clips:** `play` also takes a `.npz` from milli-motions (BONES-SEED retargeted to this duck: `joint_names`, `joint_pos`, `fps`; local only, its licence keeps it out of the repo; the beak is left out). `--telemetry` streams the duck, the IMU and the goal pose to the twin (`twin.py --remote <pi>`: the goal as a see-through blue duck, joints red past 1.5 deg with their mA), `--log play.csv` keeps every tick. Held in the air, at the policy's leg gain:
`python motion.py play clips/dance_party_hips_003__A464.npz --hz 50 --gain 800 --speed 0.5 --max-start 180 --max-loop 360 --ease-back 4 --min-volts 4.0 --telemetry --log play_dance.csv`. In the pinned simulator the dance runs at half speed with 8 deg worst lag; the walk stops at 16 s there, as the pinned body pushes the feet into the floor.

`replay_log.py LOG.csv --from -3 --speed 0.1` replays a run_policy.py log in a twin window: the measured duck solid, the goals as a see-through blue duck, slowed and looped.

**Try the sample:** `motions/head_look_around.json`, 20.6 s.

**The simulator's servo friction, fitted to the real duck** (2026-11-24): with microduck's 0.0048 N m of joint friction the simulated duck, every servo holding the stand pose at P 800 and no policy, fell forward in 0.6 s; the real one stands there. Friction alone didn't fix it, as MuJoCo's lets a loaded joint creep (0.3 N m only delayed the fall to 2.5 s). 0.07 N m that holds (`solimpfriction="0.999 0.9999 0.001 0.5 2"`, as the 288:1 gearbox does) matches both measurements: standing, the right knee 3.8 deg past its goal and the body 6.0 deg nose down (real: 3.4 and 6); a 6 deg kick in the air at about 85 ms to 90 % and 0.3-1 deg short at the end (real: 55-83 ms, 0-1.3 deg). It's set in `spec/actuators.json` (XL330_M288 `friction_nm`, `friction_solimp`), written by `tools/make_rl_model.py`, and in the trainer's Dynamixel models and `sim/model/milli.xml`; `sim/server.py --friction` overrides it. In that simulator the stand_nod policy that shook the real duck jolts at the hand-off (legs 23 deg off the stand), then stands dead still; on the real duck the jolt was about 3 times as violent (joints at 5.9 rad/s against 2.7) and pulled the supply to 3.3 V in 0.5 s, which stopped it.

**The stand policy's shake on the real duck, and Pollen's servo model** (2026-11-24): on the 6 V supply the policy took over, and within 1 s its wobble grew (6-7 Hz in the gyro) until every servo sat at its current cap and the supply fell to 2.9 V. In the simulator the same policy settled every time: with the measured gear friction, the 800 mA cap, +40 ms of servo delay, IMU and joint-speed delays as measured on the real duck (~20 ms each, the gyro repeating a stale reading on 6-25 % of ticks), springy soles, and in milli-rl on Pollen's measured XL330 model (BAM m6, which microduck uses on the same servos and milli's Dynamixel tasks had replaced with a plain DC motor). Only an 80 ms IMU delay made it shake and fall. The recipe had randomized the IMU delay over 0-20 ms and the joint speeds at 20 ms: the real duck sat at the edge. So milli-rl's `Mjlab-StandHand-Flat-Milli-Dynamixel-Bam` (milli_bam_env_cfg.py) trains the stand on BAM at the real gains and 5.4-6.0 V with the IMU 0-60 ms and the joint speeds 20-40 ms old (`train_stand_bam.sh`, exported as `models/stand_bam.onnx`). In it the old stand policy falls within ~1 s. Trained 1500 iterations from stand_nod (episodes 51 -> ~900 steps): on BAM from starts tilted up to 20 deg, 99.6 % of 256 stay up 10 s, 95.3 % with pushes; in `sim/server.py` it stands after the hand-off with the IMU 80 ms late, where the old policy fell (render: `docs/images/policies/dynamixel/stand_bam_handoff.mp4`). The launcher's RT + A now runs it (`--model models/stand_bam.onnx --bam`). **First real run, 2026-11-24 19:50: it stood under the policy, calm, about 16 s** (body tilt 1-2.5 deg, servo currents 36-54 mA where the old policy pinned every servo at 700-890 mA, the 6 V supply steady at 5.9-6.0 V), head commands too; then 13 of the 15 servos stopped answering at once (a bus or power connection, not the policy) and it eased down. BAM models position mode, so its policies run with `run_policy.py --bam` (mode 3, P 800/1200/600, D 0, no current cap). `sim/server.py` gained `--imu-lag-ms`, `--vel-lag-ms` and `--sole TIMECONST DAMPRATIO` for these tests.

**If the Pi drops off the Wi-Fi for good** (2026-11-24): a power cut while NetworkManager rewrote the Wi-Fi profile left `/etc/netplan/` with only the eth0 file, so the Pi booted (Bluetooth fine) but never joined. The card's boot partition still has the original `network-config`. Changing the instance ID in both `meta-data` and `cmdline.txt` (`ds=nocloud;i=...`) to a new value makes cloud-init treat the next boot as a first boot: it writes the Wi-Fi again from `network-config`, keeps `~/duck` and the pairing, and makes new SSH host keys. The cause is the servos sharing the Pi's supply: give the Pi its own supply, so a servo sag can't reset it. The head starts folded down in front, swings up and over to lean back, looks to one side, and comes back down; the legs barely move.

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
