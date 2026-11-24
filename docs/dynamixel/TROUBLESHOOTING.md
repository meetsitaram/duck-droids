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

**Seen:** the real duck's battery is under the head, in front of the neck, and its bus board on the back of the head, not as in the model (battery in the body). The model's balance therefore doesn't match: its "balanced" head pose tipped the real duck forward, and the hand-found head pose a little back. Nothing in the test can tell: it uses no IMU, and a falling duck doesn't load its servos, so the log looks normal.

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

**Also seen:** several joints' currents flip sign every reading under the policy, the head yaw at +-400 mA while told to hold still: the duck shaking, not holding. Low voltage makes the servos weaker and slower, which can cause it. Look again once the supply holds; if it stays, it's a mismatch of gains or delays between the sim and the duck.

**Earlier in that session:** the IMU vanished from I2C and the servos showed red alarm LEDs after a wiring fault (fixed by the user); and `i2cdetect` run every 5 s by a monitor while the IMU was read caused 0.5 s gaps in its readings: don't scan the bus while a run uses the IMU.

### The servo UBEC flashes red, with either battery (2026-11-24)

**Seen:** after the stand attempts above, the ZTW UBEC 8A (jumper on 6.0 V) that feeds the servos flashes its LED red, with both 2S packs on hand. Not yet diagnosed; both packs are charging overnight.

**To check, in order:** each pack's voltage at its plug, resting and fully charged (8.4 V full; a 2S pack is flat at 6.6-7.0 V); the UBEC's input under load (it needs 7 V or more in); what the red light means in the ZTW manual for this model (it may be its low-input or protection warning, not a fault); the UBEC's output at the bus board's terminals while the duck stands. If a fresh pack still makes it flash, suspect the UBEC or its input wiring. The supply's collapse past about 4 A in the entry above may be this same fault.
