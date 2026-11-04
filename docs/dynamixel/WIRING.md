# Wiring the all-Dynamixel duck

Nothing here has been built. Connector positions are from ROBOTIS's own XL330 model.

## Power

| Rail | From | Feeds | Worst case |
|---|---|---|---|
| Battery, 7.4 V nominal, **8.4 V full** | 2S 450 mAh 60C, on its XT30 | all 15 XL330s, directly, as Microduck's trainer models its own. **Past ROBOTIS's 6 V maximum** | 27 A from the pack. All 15 stalling at 5 V would be 22 A (1.47 A each, per ROBOTIS), and more at 7.4 V: expect the pack's voltage to sag first |
| Logic 5 V | 1 UBEC, 8 A, jumper at 5 V: **measure it before connecting anything** | Pi Zero 2 W, IMU (through the Pi). The bus board's logic comes over its USB-C | under 1.5 A |

No power switch is designed in: unplug the XT30. Each JST EH lead is rated by ROBOTIS's 21 AWG crimp at about 3 A, so power each leg and the neck by its own lead from the battery, rather than one chain through all 15.

## Signals

| From | To | How |
|---|---|---|
| Pi micro USB (the port marked USB), right-angle OTG lead | Waveshare Bus Servo Adapter (A), USB-C | both jumpers at B. Right-angle at both ends: there is 11 mm beside the board and little under the Pi |
| Bus board's 2 sockets | the chains | D, V, G. V is only what its DC terminals are given. Your Koch arm needed its sockets eased to take Dynamixel plugs: do it before fitting |
| Battery lead, in the neck | bus board's DC terminals | feeds the head's chain. **Its silkscreen says DC 9-12.6 V, and the pack is 7.4-8.4 V. Bench test first** |
| Pi I2C (pins 3, 5), 3V3, ground | IMU in the body | 4 thin wires down the neck |
| Pi GPIO, ground | foot switches | 2 wires down each leg |
| Pi camera port | camera | its ribbon. Leave slack: the camera is on the hood, the Pi on the frame |

## The chains

Each servo has 2 sockets, wired through, and the 15 share one bus with IDs 1-15.

- **Left leg:** body -> hip yaw -> hip roll -> hip pitch -> knee -> ankle.
- **Right leg:** the same.
- **Head:** body -> neck -> head pitch -> head yaw -> head roll -> beak.

## Where the wires go

The sockets are in notches at the long edges of each servo's rear face, 4-14 mm from the shaft, their tops 3.1 mm under the face. A plug stays inside the case's outline, and its wires leave sideways, or out the back.

| Servo | Way out |
|---|---|
| Hip pitch, knee | out the back, through 2 windows in the thigh plate, into the 3 mm gap under the cover, to the cover's open inside |
| Hip yaw, hip roll, ankle, neck, head pitch, head yaw | sideways |
| Head roll, beak | sideways; one side through a groove in the plate lying against it |

Across each joint, leave a loop for its whole range. Then move every joint by hand, end to end, before powering up.

## What is not designed

- A power switch.
- Wire clips and exact lengths: measure on the build.
- Speaker and microphone.
