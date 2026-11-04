# Wiring milli

Nothing here has been built. Connector positions for the STS3215 come from SO-101's mesh; for the XL330 from microduck's model, which is simplified: check a real one.

## Power

| Rail | From | Feeds | Worst case |
|---|---|---|---|
| Battery, 7.4 V nominal, **8.4 V full** | 2S 850 mAh 50C, on an XT30 | the 10 STS3215s, directly, and both regulators | 42 A from the pack. A small JST plug won't carry this |
| Servo 5 V | left UBEC, 8 A | XC330 and 4 XL330s | 7.7 A if all stall (1.80 + 4 x 1.47 A, per ROBOTIS) |
| Logic 5 V | right UBEC, 8 A | Pi Zero 2 W, IMU (through the Pi), FE-URT-1 logic, U2D2 | under 1.5 A |

Both UBECs have a 5 V / 6 V jumper. **Set 5 V and measure before connecting anything:** 6 V is over the XL330's rating only slightly, and over the Pi's by a lot.

A full pack is above the 7.4 V most sellers give for the STS3215 (one says 8.4 V). Open Duck Mini runs STS3215s on 2S; confirm yours on a single servo first.

## Signals

| From | To | How |
|---|---|---|
| Pi UART (pins 8, 10) and ground | FE-URT-1, UART side | 3 short wires |
| FE-URT-1 servo port | down the neck to the body | **data and ground only**: leave its power pin off, so walking current doesn't run through the neck. The battery feeds the chain in the body |
| Pi micro USB, OTG lead | U2D2 | |
| U2D2 | XL330 / XC330 chain | data and ground from the U2D2; the 5 V servo rail spliced in. The U2D2 gives no power |
| Pi I2C (pins 3, 5), 3V3, ground | IMU in the body | 4 thin wires down the neck |
| Pi GPIO, ground | foot switches | 2 wires down each leg, beside the chain |
| Pi camera port | camera | the ribbon that comes with it. Leave slack: the camera is on the hood, the Pi on the frame |

## The chains

Each servo has 2 sockets, wired through, so each chain is one line.

- **Feetech, left and right:** body -> hip yaw -> hip roll -> hip pitch -> knee -> ankle. The two legs share one bus: IDs 1-5 and 6-10.
- **Dynamixel:** body -> neck -> head pitch -> head yaw -> head roll -> beak. The 180 mm leads that come with each servo.

## Where the wires go

| Servo | Sockets | Way out |
|---|---|---|
| Hip yaw | rear face, up through a window in the top plate | inside the body, under the shell |
| Hip roll | rear face, through a window in its tray | back, then out to the thigh, leaving slack for roll and yaw |
| Hip pitch, knee | rear face, through windows in the thigh plate, under the cover | a notch in the plate's top edge (from the hip) and its back edge (to the shin), to the cover's open inside |
| Ankle | rear face, through a window between the plate's 2 rails | **tie the wires straight up the rail.** The shoe's inner ear passes within 1 mm of the plug past about 1 rad, and would catch a loop |
| XL330, XC330 | in the notches each side of the case by the horn, per microduck's model | out sideways |

Across each joint, leave a loop for its whole range. Then move every joint by hand, end to end, before powering up.

## What is not designed

- A power switch: unplug the XT30.
- Wire clips and exact lengths: measure on the build.
- Speaker and microphone.
