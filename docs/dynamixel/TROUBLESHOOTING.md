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

## Power

### An XL330 on the 2S battery goes limp (found in the manual, 2026-11-20)

**Seen:** nothing yet: caught before powering a servo. ROBOTIS's XL330-M288 manual gives 3.7-6.0 V, 5.0 V recommended, and a Max Voltage Limit of 7.0 V that can't be set higher. Past it the servo flags an input voltage error and, by default, turns its torque off till it's rebooted. The 2S pack is 7.4 V nominal and 8.4 V full.

**Fix:** set ids and test on 5 V. `set_id` refuses past 6.0 V. For the robot: a 6 V regulator between the battery and the bus board, not designed in yet.
