# Troubleshooting the all-Dynamixel duck

What went wrong on the real hardware, and what fixed it. Newest at the bottom of each section. Add to it as things come up.

## The bus board

### Windows says "USB device not recognized", and no COM port appears (2026-11-21)

**Seen:** the Waveshare Bus Servo Adapter (A) came up as a COM port the first time, USB only. After 5 V was put on its green terminals, every later plug-in failed. Device Manager showed "Unknown USB Device (Device Descriptor Request Failed)", the same on every port, after removing the device and rescanning, and with a second board. Dynamixel Wizard couldn't scan either: there was no port for it to open.

**Cause:** the order things were powered. Each failure was the USB plugged in while 5 V was already on the terminals: the board's USB chip powers up from the 5 V before the PC talks to it, and doesn't start properly. Unplugging the USB alone doesn't reset it, as the 5 V keeps it powered. Not the board, not the cable: both boards and both cables worked once the 5 V was off.

**Fix:** USB first, then 5 V. To unplug, 5 V off first, then USB. If it's already stuck: take off the 5 V and the servo, unplug the USB, wait 5 s, plug the USB back in. Windows can take up to a minute to show the COM port.

**Not the fix:** removing the failed device and rescanning (`pnputil`, as admin), or another program. Both change nothing while the 5 V is on.

### A script hangs and Windows won't kill it; the port then says "Access is denied" (2026-11-21)

**Seen:** `python -m duck.set_id --find` hung. `taskkill /F` couldn't end it, and COM3 stayed locked.

**Cause:** opening the board's CH343 USB chip at 3-4.5 Mbps could wedge its Windows driver, and a read that only timed out when the line went quiet could wait for ever.

**Fix:** unplug the board's USB: that ends the stuck process and frees the port. `set_id` now stops at 2 Mbps when searching, and every read in `pi/duck/dxl.py` gives up after its time limit.

## The servos

### A servo arrives at id 14, not id 1, and refuses to move: error 0x6 (2026-11-21)

**Seen:** the first XL330-M288 answered at id 14 and 1 Mbps, not a new XL330's id 1 at 57600. Its id changed fine, but the first move was refused: `refused write at 116: error 0x6`, a Data Limit Error, the goal outside its position limits.

**Cause:** it came set up for another robot, probably as one of Seeed's numbered Reachy Mini servos: homing offset -1000 and position limits 1035-2356, about 116 degrees, instead of 0 and 0-4095. The offset would also shift every position the duck reads by 1000 ticks, 88 degrees.

**Fix:** `set_id` now resets each servo to factory settings but keeps its new id and 1 Mbps (Factory Reset, keep id and baud), and checks the offset and limits came back. What it had before is kept in `pi/config/servos.json`, as `settings_before_reset`. In Dynamixel Wizard: Factory Reset, then set the id and baud again.

### A mounted joint stops 3-4 degrees short of where it's told (2026-11-21)

**Seen:** the right hip roll (id 4), in its joint, nudged 10 degrees each way at the factory position gain (P 400): moves one way got there, moves the other way stopped 4-4.5 degrees short, every time, at 40 mA and no hardware error. With its torque off it sagged the same way, 2054 to 2250. Turned by hand it covers 1822-2314, 43 degrees, against the design's 38 (+-0.33 rad), so the stops are outside the limits, as they should be.

**Cause:** the leg's weight. A position servo pushes in proportion to how far off it is: 4 degrees off at P 400 is about 6% power, not enough to lift the leg the last few degrees. Not the servo: at P 1600 every move came within 1 degree.

**For later:** `pi/config/dynamixel.json` runs the servos at `position_p` 200, half the factory gain, so a standing duck will sag further off its targets unless the policy was trained for it. Check the gain the policy was trained with against this before walking. And test each joint about its own centre: from a sagged position a 10 degree nudge can run into a stop.

### Both hip yaws have their middle at the servo's 0/4095 wrap (2026-11-21)

**Seen:** with each hip yaw set to its middle by hand, the right one read 8-16 and the left one 126, both next to the point where a turn's 4095 wraps to 0. The hip yaw needs +-26 degrees, +-296 ticks, so its range crosses the wrap, which position mode (3) can't command: a goal must be 0-4095. Both servos nudge fine; the right one went 10 degrees each way in extended position mode (4).

**Cause:** the horn fitted with the servo near 0 rather than mid-range. Every other joint's middle so far is 1008-3070, well inside.

**Fix:** when the hips come apart, refit each yaw's horn with the servo at about 2048 and the joint at its middle: `python -m duck.set_id --find` reads the servo, or watch its position live while turning it. Until then, the duck's code would have to run both yaws in extended position mode. A homing offset to shift the reading was tried on the right yaw: stored, but its reading didn't change, even after a reboot. Not understood yet.

### Joint readings past the design's limits, with the duck sitting (2026-11-21)

**Seen:** all 15 on one bus, torque off, the duck sitting folded with its head down. Measured from each servo's middle as set by hand before assembly: knees -93 and +94 degrees, ankles -90 and +91, neck +69, head pitch +66. The right knee's limit is -63 and the neck's +9.

**Cause:** those middles were set on loose servos, so they aren't the joints' zeros, and some joints may turn the other way to the config's `direction: 1`. The neck's +69 only makes sense as head down.

**Fix:** calibrate with the duck posed at zero, legs straight, head level, beak shut: `python -m duck.calibrate` reads each servo and writes its centre, and moves nothing. Then check each joint's direction, on the stand or against the digital twin.

## Standing up (pi/stand_test.py)

### The knees trail 12 degrees and the supply sags under 4.6 V (2026-11-21)

**Seen:** with a hand only steadying it, the knees took the duck's weight: about 450 mA each at gain 800, trailing 12 degrees, and the 5 V bench supply fell from 5.1 to 4.5 V at 1.2 A in all. At gain 1500 with a 12 s rise the knees stayed within about 3 degrees and the supply at 4.8 V, at 0.6 A; with more of the weight on them, 0.7 A a knee and 1.5 A in all, the supply fell to 4.3 V.

**Fix:** a supply that holds 5-6 V at 5 A or more, on short thick leads, or the battery through a 6 V regulator, which the robot needs anyway. Meanwhile a slow rise and a hand under the body.

### A stop dropped the duck from half standing (2026-11-21)

**Seen:** the supply sagged under the stop's 4.6 V; the test held 15 s and then turned the torque off with the duck half up. It fell onto the table, undamaged.

**Fix:** a stop now eases the duck back down to the pose it started in (sitting) over `--abort-lower` seconds, and only then turns the torque off. Lowering takes less current than holding, so a sagging supply can still do it.

### It tips back, or forward, while rising (2026-11-21)

**Since then (2026-11-24):** the battery is on the back of the main body, as in the model; the notes below describe the layout of 2026-11-21. **Seen then:** the real duck's battery was under the head, in front of the neck, and its bus board on the back of the head, not as in the model (battery in the body). The model's balance therefore doesn't match: its "balanced" head pose tipped the real duck forward, and the hand-found head pose a little back. Nothing in the test can tell: it uses no IMU, and a falling duck doesn't load its servos, so the log looks normal.

**Fix for now:** set the neck and head by hand where the duck balances (`--keep-head`), raise the neck a little (`--neck-offset -10`, the weight forward), keep the face straight ahead (`--face-forward`), and move the head only side to side or a little, slowly, front to back. Later: put the real layout into the model, and run the test from the Pi, where the IMU is.

### The neck works hardest standing (2026-11-21)

**Seen:** with the battery under the head and the neck raised, the neck held 200 mA standing, a third of its 600 mA cap, and the left knee about five times the right (118 against 24 mA): the weight sits a little left. Warm after long holds: watch its temperature.

### The head shakes after turning side to side (2026-11-21)

**Seen:** every servo at the legs' gain, 1500: after the side-to-side turn the head yaw hunted round its goal, up to 0.7 degrees about 17 times a second, and kept on until the duck sat. Its error changed sign 203 times in 914 ticks; every other joint, 0 to 6.

**Cause:** a stiff servo with a heavy head on it and almost nothing resisting the motion overshoots, corrects and overshoots again, and nothing damps it.

**Fix:** the head and beak at gain 600 with damping (D 300), the legs left at 1500, and the turn slower (1.2 s a swing).

### The neck trails a fast lift and stops the run (2026-11-21)

**Seen:** a recorded motion lifting the head over the top at about 65 degrees a second: with the neck soft and damped like the head, it fell 17.9 degrees behind at only 320 mA, and the lag stop ended it.

**Fix:** the neck its own setting, stiff like the legs (gain 1200, D 100): it lifts the whole head. At half speed it then kept within 12 degrees, at 475 mA, and the supply sagged to 4.5 V, under the 4.6 V stop: with `--min-volts 4.2` it played through. The supply again: see the first entry.

### The board that steps the battery down sags (2026-11-21)

**Seen:** a buck board on hand, sold as 9-36 V in and 3.5-6 A out, fed from the 2S pack, 7.4 V nominal: under its 9 V minimum it can't regulate, and the servos' supply sagged under 1-1.5 A.

**Fix:** a servo BEC that runs from 2S: about 6 V minimum in, 5-6 V out, 5 A or more continuous, switching, no USB port (a USB one can switch to 9 or 12 V for quick charging). The ZTW UBEC 8A G2 (7-34 V in, 8 A, 15 A peak, jumper on 6.0 V) or a 5 A Hobbywing UBEC. On the back of the torso, the legs fed from it there, thick leads up the neck to the bus board. Measure its output before connecting the servos.

## Power

### An XL330 on the 2S battery goes limp (found in the manual, 2026-11-20)

**Seen:** nothing yet: caught before powering a servo. ROBOTIS's XL330-M288 manual gives 3.7-6.0 V, 5.0 V recommended, and a Max Voltage Limit of 7.0 V that can't be set higher. Past it the servo flags an input voltage error and, by default, turns its torque off till it's rebooted. The 2S pack is 7.4 V nominal and 8.4 V full.

**Fix:** set ids and test on 5 V. `set_id` refuses past 6.0 V. For the robot: a 6 V regulator between the battery and the bus board, not designed in yet.

## The Pi and the gamepad

### The Xbox controller pairs, then connects and drops in a loop, its logo flashing (2026-11-23)

**Seen:** an Xbox Series X|S controller (Bluetooth LE, USB id 045e:0b12, 0b13 over Bluetooth) on the Pi Zero 2 W's built-in Bluetooth, Raspberry Pi OS Lite on Debian 13. `bluetoothctl` said "Pairing successful" and "Connection successful", but the logo kept flashing, and no button ever reached the Pi: `/dev/input/event2` came and went every second or two ("No such device" on reading it). `journalctl -b | grep bluetoothd` showed `report_map_read_cb() Report Map read failed: Request attribute has encountered an unlikely error` and `Unable to set wake_support without RPA resolution`. Earlier, `bluetoothctl power on` failed (`org.bluez.Error.Failed`): Raspberry Pi OS starts with Bluetooth soft-blocked (`/sys/class/rfkill/*/soft` was 1).

**Cause:** a known clash between these controllers and the Pi's internal Bluetooth adapter (xpadneo's `docs/TROUBLESHOOTING.md`, "Controller keeps blinking"): the connection times the Pi asks for don't suit the controller, which gives up on the link before it has read the Pi's HID setup, and without LE privacy the Pi doesn't give the controller the identity it needs to reconnect.

**Fix:** `sudo bash pi/xbox_pair.sh` (in `~/duck` on the Pi) does it all: in `/etc/bluetooth/main.conf`, `[General]` `Privacy = device`, `JustWorksRepairing = always`, `FastConnectable = true`, and `[LE]` `MinConnectionInterval = 7`, `MaxConnectionInterval = 9`, `ConnectionLatency = 0`, `ConnectionSupervisionTimeout = 200`; then it removes the old pairing, pairs and trusts the controller again (hold its pair button when asked), and writes the same per device in `/var/lib/bluetooth/<adapter>/<controller>/info`: `[ConnectionParameters]` `MinInterval=6`, `MaxInterval=6`, `Latency=0`, `Timeout=300`. After that the logo went steady and every button and stick reached the Pi. `setup_pi.sh` unblocks Bluetooth (`rfkill unblock bluetooth`).

**Pairing again wipes the per-device part:** holding the controller's pair button (or pairing it to a PC) means running `xbox_pair.sh` again.

**Not the fix, on its own:** `Privacy = device`, `JustWorksRepairing = always`, `UserspaceHID=true` and `disable_ertm=Y` (all still set), a reboot, removing and pairing again, and a controller firmware update through the Xbox Accessories app on Windows (cancel its sign-in prompt: the update doesn't need an Xbox account). Each still looped. What tipped it was the LE connection parameters.

**Keep Bluetooth on the Pi's main UART.** `setup_pi.sh --uart` (the bus board on the UART, the fallback) moves it to the mini UART, which may make this worse. If the controller loops again, the next step is a USB Bluetooth adapter, which needs a micro USB hub as the bus board takes the Pi's only data port.

### The controller was working, then nothing arrives (2026-11-23)

**Seen:** paired and tested, then idle a while; `run_policy.py --pad-check` shows `LOST`, `bluetoothctl info` says Connected: no, and `bluetoothctl connect` says `InProgress`. Pressing A, B and the sticks does nothing.

**Cause:** the Xbox controller switches itself off after about 15 minutes without use. Only the Xbox button wakes it.

**Fix:** press the Xbox button: it reconnects to the Pi by itself in a few seconds (logo steady), no re-pairing. If the logo keeps flashing slowly instead, run `sudo bash xbox_pair.sh` again. While the duck stands, a dropped controller sits it down after `--pad-lost` seconds.

### The Pi rebooted as the policy took over, then wouldn't start: a damaged regulator (2026-11-23)

**Seen:** the first stand from the controller (`run_policy.py --pad`). The scripted rise went fine (the servos' supply 6.1 V sitting, 5.8 V by the end of the rise), then about 1 s after the policy took over the Pi rebooted. Nothing was logged: the journal isn't kept across boots, and the run's CSV was still in memory. The servos, on their own power, held the policy's last goals, a strange half-standing pose. After a battery swap the Pi's green LED stayed dark: no power at all.

**Cause:** the voltage regulator feeding the Pi was damaged. Replaced, the Pi booted with no undervoltage (`vcgencmd get_throttled` 0x0). Whether it failed in the first stand, or was failing already and caused the reboot, isn't known.

**Since then:** `run_policy.py` writes its log to disk every second and records the Pi's undervoltage flag every tick (column `pi_throttled`, a warning printed if the Pi's 5 V dips), so the next dropout leaves a record. Feed the Pi's 5 V converter from the battery side (7.4-8.4 V), not the servos' 6 V rail: it needs 6 V or more in, and the rail sags under load.

**If the Pi dies with the servos on:** they keep holding their last goals. Hold the duck, then from the PC ease the legs back to sitting and turn the torque off (as done that day), or switch off with a hand on the duck.

### The policy takes over and the servos' supply collapses to 4.3 V (2026-11-23)

**Seen:** the third stand from the controller (`run_policy.py --pad`, log `stand3_log.csv` on the Pi). The rise was fine (5.8 V at under 0.7 A in all). About 1 s after the policy took over, the safety stop: supply 4.3 V. The Pi's own 5 V held (`pi_throttled` 0 throughout). The servos' supply against their total current: 5.8 V at 0.4-0.7 A, 5.1 V at 2.1 A, 5.0 V at 3-4 A, then 4.3 V past about 4.2 A.

**Cause:** the servos' power path drops about 0.3 V per amp and gives out past about 4 A: the regulator (a USB-type or small buck can't hold 6 V at these currents), thin or long leads, or a connector. The policy's first second asks for 2-4 A and more in bursts (knees to 0.88 A each).

**Fix (to do):** a supply good for 8 A at 6 V, such as the ZTW UBEC 8A in the entry above, with short, thick leads to the bus board; then measure the voltage at the bus board's terminals during a stand.

**Also seen:** several joints' currents flip sign every reading under the policy, the head yaw at +-400 mA while told to hold still: the duck shaking, not holding. Low voltage makes the servos weaker and slower, which can cause it. Look again once the supply holds; if it stays, it's a mismatch of gains or delays between the sim and the duck. **Found (2026-11-24):** it stayed on a steady supply. It was the policy shaking, trained on a plain motor model with no margin on the IMU's delay: see "The stand policy shakes at the hand-over" and "Our mistake" below.

**Earlier in that session:** the IMU vanished from I2C and the servos showed red alarm LEDs after a wiring fault (fixed by the user); and `i2cdetect` run every 5 s by a monitor while the IMU was read caused 0.5 s gaps in its readings: don't scan the bus while a run uses the IMU.

### The servo UBEC flashes red, with either battery (2026-11-24)

**Seen:** after the stand attempts above, the ZTW UBEC 8A (jumper on 6.0 V) that feeds the servos flashes its LED red, with both 2S packs on hand. Not yet diagnosed; both packs are charging overnight.

**To check, in order:** each pack's voltage at its plug, resting and fully charged (8.4 V full; a 2S pack is flat at 6.6-7.0 V); the UBEC's input under load (it needs 7 V or more in); what the red light means in the ZTW manual for this model (it may be its low-input or protection warning, not a fault); the UBEC's output at the bus board's terminals while the duck stands. If a fresh pack still makes it flash, suspect the UBEC or its input wiring. The supply's collapse past about 4 A in the entry above may be this same fault.

### The supply falls to 3-4 V the moment a policy moves: the power path, and the Pi sharing it (2026-11-24)

**Seen:** with the servos fed from a 5 V 10 A bench supply, the old stand policy pulled the bus voltage (read by the servos) from 5.1 V to 3.3 V within 0.5 s of taking over; a full-speed walk replay at gain 1500 to 3.9 V at about 1.7 A; on a 6 V regulator, the old policy still to 2.9 V once every servo sat at its cap. After one rewire the Pi shared the servos' supply, browned out mid-walk and reset; its servos, left powered with nothing in charge, held their last goals at gain 1500 and shook.

**Cause:** about 0.6 ohm between the supply and the servos (5.2 V to 3.9 V at under 2 A): leads, connectors, the bus board's input. A 10 A supply means nothing through that. And a policy that shakes asks every servo for its cap at once, 10 A or more.

**Fix:** the servos on their own 6 V regulator (5 A or more, short thick leads to the bus board's terminals: 5.8-5.9 V idle, 5.3-5.5 V rising), the Pi on a supply of its own so a sag can't reset it. `run_policy.py` stops only when the voltage stays under `--min-volts` for 2 readings in a row (1 s), so one dip doesn't end a run. **Never a 2S pack straight onto the XL330s:** 7.4 V nominal, 8.4 V full, past their 6 V rating (microduck does run them so, at 6.5-8.2 V). A policy that doesn't shake (stand_bam, below) stands at 36-54 mA a servo, and the supply holds at 5.9-6.0 V.

### The Pi boots (Bluetooth works) but never joins the Wi-Fi (2026-11-24)

**Seen:** after the brownout above, the Pi came up (the controller paired over Bluetooth), but no Raspberry Pi address showed anywhere on the network. Reading the card on the PC (a read-only ext4 reader, the Python `ext4` package, through one admin prompt; WSL can't attach USB card readers): `/etc/netplan/` held only the eth0 profile, `/etc/NetworkManager/system-connections` was empty, and NetworkManager's timestamps showed the Wi-Fi last connected at 16:16, mid-crash.

**Cause:** a power cut while NetworkManager rewrote the Wi-Fi profile. Linux writes a new copy and renames it over the old one, and the rename never reached the card.

**Fix:** the card's boot partition still had the original `network-config`. Give `meta-data`'s `instance-id` and the `ds=nocloud;i=...` in `cmdline.txt` the same new value: cloud-init treats the next boot as a first boot and writes the Wi-Fi profile again, keeping `~/duck` and the pairing, with new SSH host keys. Raspberry Pi Imager can't do this: it only writes whole new images. Ways in when the Wi-Fi is down: a 3.3 V USB-serial adapter on pins 8/10 (the serial console is already on, `console=serial0,115200`). USB gadget mode is out, as the bus board takes the Pi's only data port.

### The IMU goes silent during a stand, and the policy never takes over (2026-11-24)

**Seen:** the BNO085 reset itself mid-run (its debug packet dump in `launcher.log`, 6 times that day), with the servos working. Once its reading froze 4 s into the rise; `run_policy.py`, which waits for a live IMU before handing over, held the scripted stand 10 s and sat down ("IMU silent"). The reader's own restarts (after 0.3 s of silence) didn't bring it back that time. Another time it came back on a different address and `telemetry.py` died on it.

**Fix so far:** `telemetry.py` streams the servos without the IMU if it won't start, and a power cycle brings the IMU back. **Open:** why it resets under servo load: its power or I2C wires beside the servo leads, or the I2C clock (400 kHz). Watch for the dump in `launcher.log`.

### A missed bus reading crashed the run and dropped the duck; later 13 servos stopped at once (2026-11-24)

**Seen:** at the hand-over one sync read timed out; `run_policy.py` had no handler, crashed, and the torque went off. Later, after 16 s of a good stand, 13 of the 15 servos stopped answering together.

**Fix:** a missed reading reuses the last one; 5 in a row (100 ms) stop the run, naming the servos that no longer answer a ping, and ease the duck down from the last position read instead of dropping it. **Open:** the 13 at once is a bus or power connection (currents were 36-54 mA and the supply steady just before): check the bus leads and the 6 V lead at the head board.

## Calibration (2026-11-24)

### It leans right standing, and calibrating by eye moved good zeros (2026-11-24)

**Seen:** the scripted stand leaned right, and a policy hand-over thrashed. The right knee's zero was 12.2 deg off (read with the thigh and shin flat on the table). Calibrating by eye then moved two good zeros (left knee -4.1, left ankle +6.9 deg) and once took a hip pitch at -87 deg.

**Fix:** `calibrate.py`: one joint at a time from the ankles up, every other servo held, the twin colouring that joint yellow, done ones green, the rest grey, with the reference for it on screen (knee: thigh and shin flat on the table; ankle: foot flat, shin upright; hip roll square to its servo; hip pitch straight down from the side; hip yaw foot straight ahead). A sets the zero, B keeps the old one; a change over 20 deg needs A twice; each zero is saved at once. By hand the zeros are good to about 5 deg. Check them with a contact pose (knee shells and face on the table, against the model's rest) and the lift-and-set-down test (`motor_test.py --no-kicks --settle 120`: lifted, every leg joint was within 0.6 deg of its goal, so the zeros hold).

### The IMU read the body 9.7 deg more nose-down than it was (2026-11-24)

**Seen:** lying on its knee shells and face, where the model rests 2.0 deg nose-up, the IMU said 7.7 deg nose-down, and the twin, which tilts by the IMU, floated the knees off the table. A policy fed that thinks it's always falling forward: a 7 deg bias reproduced the hand-over thrash in the sim.

**Fix:** `imu_to_robot` turned 9.7 deg in pitch to match the CAD (noted in `config/dynamixel.json`). Check: standing still on the table for 60 s, the IMU read +0.3 / +0.3 deg against the model's 0 / 0 (`motor_test.py --no-kicks --settle 60`, which writes `stand_tilt.csv`).

### The right knee bends 3.4 deg past its goal standing (2026-11-24)

**Seen:** lifted, every leg joint within 0.6 deg of its goal; on the table the right knee 3.4 deg past it at 117 mA, the left 1.1 deg at 35 mA, the body 6 deg nose-down and 1.7 deg right side down.

**Cause:** sag, not calibration. The weight sat on the right knee, and at P 800 a joint gives about 1 deg per 35 mA, which tips more weight onto it; gear friction holds the rest. The sim fitted to the duck (below) does the same: 3.8 deg and 6.0 deg.

### The neck jams leaning back in a replayed clip (2026-11-24)

**Seen:** a retargeted walk holds the neck at +42 deg; the neck stopped at about +33 deg, pushing at its full cap for 30 s. By hand, torque off, it goes from +32 deg back to -174 deg forward.

**Fix:** `motion.py` clips every goal to the config's limits (the neck's is +8.6 deg back, for the wires), as `run_policy.py` already did. Retargets should lean the neck back less.

## The policy and the simulator (2026-11-24)

### The stand policy shakes at the hand-over until every servo is at its cap (2026-11-23/24)

**Seen:** the stand policy (stand_nod) took over, and within 0.5-1 s the body rocked at 6-7 Hz, growing (gyro -1.1 to +1.1 rad/s), joints to 6.9 rad/s, every servo at 700-890 mA, the supply collapsing. Easing the policy in (`--blend`) made it fall in the sim; capping the goals' speed only helped at 60 deg/s and made it fall at 30.

**What it wasn't:** in the simulator the same policy settled within a second with each of these: the duck's real gear friction, the 800 mA cap (0.28 N m), +40 ms of servo delay, the IMU and joint-speed delays as measured on the duck (each about 20 ms: the gyro trails the leg encoders by one tick and repeats a stale reading on 6-25 % of ticks), springy soles, and Pollen's measured XL330 model. Only an 80 ms IMU delay made it shake and fall.

**Cause:** no margin. The recipe drew the IMU's delay from 0-20 ms and the joint speeds' at 20 ms, and the real duck sits at the edge of that. And our mistake, the next entry: it was trained on a plain motor model, not the measured one.

**Fix:** `stand_bam.onnx`, trained on milli-rl's `Mjlab-StandHand-Flat-Milli-Dynamixel-Bam`: Pollen's XL330 model at the real P and 5.4-6.0 V, the IMU 0-60 ms and the joint speeds 20-40 ms old, starts tilted up to 20 deg. In that sim the old policy fell within 1 s; the new one stays up 99.6 % of the time (95.3 % with pushes), and stands with the IMU 80 ms late. On the duck it stood under the policy, calm, about 16 s: tilt 1-2.5 deg, 36-54 mA a servo. It runs with `run_policy.py --bam` (the launcher's RT + A). Hold the duck firmly for the first 3 s after the hand-over: in the sim, a hand on it for 2.5 s took the jolt from 2.7 to 0.19 rad/s.

### Our mistake: the Dynamixel tasks threw away Pollen's measured XL330 model (2026-11-24)

**Seen:** in the simulator, the duck holding its stand pose with no policy fell forward in 0.6 s; the real one stands there all day. The trained policies leaned on a duck that didn't exist.

**Cause:** milli-rl is Pollen's microduck_rl, and microduck runs the same XL330-M288. Pollen identified it (BAM 'xl330' m6, `bam/params/xl330/m6.json`): voltage-driven position control, and friction that grows with the torque through the 288:1 gearbox (`load_friction_motor` 0.27: a quarter of the motor's torque lost in the gears, which is what lets a geared servo hold a load). milli started on Feetech servos with a plain `DcMotorActuator`, and when it moved to XL330s that model stayed (`milli_velocity_env_cfg.py`: "friction randomization acts only through microduck's BAM servo model (a no-op on these plain actuators): replaced"). Only BAM's small fixed friction, 0.0048 N m, was copied into the model files; the load-dependent part was lost, and its `expand_bam_friction_fields` event was dropped too.

**Fix:** the joint friction fitted to the real duck, 0.07 N m that holds (`solimpfriction 0.999`: MuJoCo's default lets a loaded joint creep, and even 0.3 N m only delayed the fall to 2.5 s), in `spec/actuators.json` and every Dynamixel model. The sim now stands with the right knee 3.8 deg past its goal and the body 6.0 deg nose-down (real: 3.4 and 6), and a 6 deg kick in the air matches (85 ms to 90 %, real 55-83 ms). And the stand trains on BAM itself (above). **For every new task on these servos, start from Pollen's actuator model, not a plain motor.** BAM was measured at 7.5 V in position mode: give it our voltage (`vin_range`) and gains (`kp_fw`), and deploy in position mode (`--bam`).

**How to check a sim against the duck:** hold the stand pose with no policy (it must stand, as the real duck does); lift and set down while standing (sag); a kick test in the air (`motor_test.py`, against `motor_test_sim/real_air.json`); and replay the real run's inputs through the policy (`replay_log.py`, and the run CSV's grav and gyro columns).

### The hand-off taps and the shaking on nudges were the soft soles (2026-11-25)

**Seen:** under the stand policies the feet buzzed and tapped at the hand-off and after small nudges, more than the simulator showed.

**Cause:** the soft soles added under the feet. Taken off, the feet sit firm on the floor and the duck is much steadier on nudges and at
the hand-off (the user, 2026-11-25). An earlier check in the simulator ("springy soles", above) didn't show it: the real soles were
softer, or damped differently, than anything the sim tried.

**Fix:** run without the soft soles. The training models' feet are hard, which now matches the duck; if soles go back on, measure their
stiffness and give the sim the same before trusting a policy on them.
