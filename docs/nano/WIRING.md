# The nano duck: wiring

Written by hand, against `spec/nano_duck.py` (where each part sits) and [BOM.md](BOM.md) (what each part is, and where its numbers come from). Nothing here has been built or measured.

## What drives what

13 hobby servos on PWM, each with its own signal wire: they can't share a bus as the other ducks' serial servos do. So the wiring is a **star**: every servo's stock 3-wire lead (25 cm, TowerPro's figure) plugs into one **servo header board** at the back of the body, and from there each signal goes to its own GPIO pin on the Pi. Power and ground are two shared 5 V buses on that board, one per regulator.

```
 2S 300 mAh LiPo --XT30--+-- D24V50F5 "L" (5 V, 5 A) --+-- L bus: left leg (5), neck pitch -- header board, + and - rows, left half
     (7.6 V nominal)     |                            +-- Pi Zero 2 W 5 V
                         +-- D24V50F5 "R" (5 V, 5 A) ---- R bus: right leg (5), head pitch, beak -- header board, right half
 Pi GPIO x 13 ------------------------------------------- header board, signal row (one wire per servo)
 Pi I2C (GPIO 2, 3) + 3.3 V + GND ------------------------ IMU (Adafruit MPU-6050)
 all grounds common: both regulators' GND, the Pi's GND, the header board's - rows
```

## The brain: a Pi Zero 2 W, the servos straight from its GPIO

The Pi sits in the body (the user's layout, 2026-11-06), on edge between the two hip yaw servos, taped to a rail on the chassis. The head holds no electronics.

**Chosen: PWM from the Pi's own GPIO with pigpio, no PWM driver board.** Compared with a PCA9685 board next to the battery:

| | Pi GPIO + pigpio | PCA9685 board |
|---|---|---|
| Mass, size | nothing added | 5.5 g and 62.5 x 25.4 x 3 mm without headers, 9 g with them (adafruit.com/product/815): the board is as long as the body is wide |
| Wiring | 13 signal wires, Pi to header board | 2 I2C wires to the board, then the 13 leads plug into it |
| Timing | pigpio times servo pulses "using the DMA and PWM/PCM peripherals", on any of GPIO 0-31 (abyz.me.uk/rpi/pigpio/): 50 Hz, 500-2500 us (its gpioServo, abyz.me.uk/rpi/pigpio/cif.html). Its steps follow its sample rate, 1, 2, 4, 5, 8 or 10 us (default 5) | 12-bit across the PWM period: about 4.9 us a step at 50 Hz, independent of the Pi |
| Risk | the pigpio daemon must be running; a Pi crash stops the pulses (servos go limp) | the board holds its last pulses if the Pi stops |

It has been done: Stanford's Pupper drives its servos from a Raspberry Pi's pins with pigpio (`pupper/HardwareInterface.py` in github.com/stanfordroboticsclub/StanfordQuadruped: `import pigpio`, `set_PWM_dutycycle` on each servo's pin). A 5 us step is about 0.45 deg over an SG90's 2000 us, coarser than its 1 us dead band but finer than its backlash is likely to be. If a step proves too coarse, start pigpio at a 1 or 2 us sample rate, or add the PCA9685: the header board's signal row is the only change.

**Not chosen: an MCU.** An RP2040 board has 16 hardware PWM channels and would drive all 13 with no daemon (an ESP32-S3 has 8 LEDC channels, docs.espressif.com, so it would need its MCPWM units too). It saves about 8 g against the Pi, but drops the Pi's Linux, Wi-Fi and the trainer's Python stack. Kept as the fallback if the Pi's timing or mass don't work out.

## Pins

BCM numbers. Avoid GPIO 2 and 3 (I2C, the IMU) and 14 and 15 (the serial console).

| Joint | Servo | GPIO | Bus |
|---|---|---|---|
| L hip yaw | SG90 | 17 | L |
| L hip roll | MG90S | 27 | L |
| L hip pitch | SG90 | 22 | L |
| L knee | MG90S | 5 | L |
| L ankle pitch | SG90 | 6 | L |
| R hip yaw | SG90 | 23 | R |
| R hip roll | MG90S | 24 | R |
| R hip pitch | SG90 | 25 | R |
| R knee | MG90S | 12 | R |
| R ankle pitch | SG90 | 16 | R |
| neck pitch | SG90 | 26 | L |
| head pitch | SG90 | 19 | R |
| beak | SG90 | 13 | R |

13 servos, not 15: no head yaw or roll (spec/nano_duck.py). Free GPIO remain for a head yaw later.

## Power

**Battery: 2S, not 1S.** The servos are rated about 4.8-6 V (TowerPro's SG90 and MG90S pages say 4.8 V operating; its reply on the SG90 page: 4.8-6 V are fine), so a bare 1S cell (3.7 V) would cut their torque. The two ways to 5 V:

| | 1S 300 mAh + boost | 2S 300 mAh + buck (chosen) |
|---|---|---|
| Converter | Pololu U3V70F5, 5 V step-up: 2.9-5 V in, 8 A typical input limit, 3.6 g (pololu.com/product/2891/specs). From a 3.7 V cell that is about 5 A out at 85 % | 2 x Pololu D24V50F5, 5 V step-down: 5 A each, 6-38 V in, 3.0 g each (pololu.com/product/2851/specs) |
| Pack | about 8 g (no page opened for a 1S pack: an estimate) | Tattu 2S 300 mAh 75C, 45 x 16 x 12 mm, 16 g (genstattu.com) |
| Energy | 1.1 Wh: half the 2S's | 2.3 Wh at 7.6 V |
| Total | about 12 g | 22 g |

The 2S costs 10 g more and doubles the run time; the 1S boost can't carry all 13 servos stalled at once. Chosen for that, and as the 6 V the buck needs at 5 A sits at the 2S's end of discharge (3.1 V a cell), not below it.

**Sized for stall.** Stall current: SG90 360 mA measured (protosupplies.com), up to about 650 mA listed (pcboard.ca); MG90S 700 mA measured (protosupplies.com). Taking the higher figures, all 13 servos stalled at once draw 9 x 0.65 + 4 x 0.70 = 8.65 A. Split in two:

- **L regulator:** left leg (3 SG90, 2 MG90S) 3.35 A + neck 0.65 A + the Pi (allow 0.5 A, not measured) = 4.5 A of its 5 A.
- **R regulator:** right leg 3.35 A + head pitch and beak 1.30 A = 4.65 A of its 5 A.

So every servo can stall at once without a regulator past its rating. From the pack that is about 46 W, about 7.5 A at 6.8 V: the 75C pack is good for 22 A, but its JST-PH plug is a small signal connector: **fit an XT30** in its place. The Pi is fed on its 5 V header pins from the L regulator, not through its micro-USB: keep the polarity right.

**Run time** (an estimate): ProtoSupplies gives 100-250 mA for an SG90 while moving. At 150-250 mA for each of 13 servos and 0.3 A for the Pi (an estimate), 2.3-3.6 A at 5 V, 13-20 W from the pack at 90 %; 80 % of 2.3 Wh lasts **about 5.5-9 minutes** of walking. A longer pack (2S 450-500 mAh, 25-30 g) would give 9-14 minutes for 10-14 g more.

## Leads, service loops, mass

Each servo's own 25 cm lead goes to the header board; none are lengthened. The longest path, the ankle's, runs up the shin's spine, the thigh's web, the roll bracket's post and the yaw link into the body: about 20 cm with its loops, so it reaches. Shorter leads are coiled at the board.

- **Ankle and knee leads** leave their servos at the near end (the strain relief, in its slot in the cradle), run up the back of the shin, and are tied through the **shin's tie slot**. A **service loop** of about 15 mm hangs behind each knee and each ankle, round the joint's axis on the case's side, so the joint turns its full range (knee -1.2 to +0.2 rad) without pulling.
- **Thigh:** hip pitch and knee leads, with the ankle's, tied through the **thigh's tie slot** in its web; a loop behind the hip pitch axis.
- **Roll bracket:** all four leads of the leg tied through the **post's tie slot**, a loop under the roll axis (+/-0.35 rad), then up past the yaw link's bar into the body: a loop round the yaw axis (+/-0.4 rad).
- **Head:** the head pitch and beak leads run down the neck plate beside each other, a loop round the neck axis (-0.2 to +1.6 rad) and the head pitch axis, and in through the open bottom of the body to the board.

Tie slots are modelled (spec/nano_duck.py, 'tie slot'); the loops and clips are not. **Wire mass:** the servos' leads are in their 9 g and 13.4 g (assumed: TowerPro gives the mass with the lead fitted, not apart). Everything else (the two 5 V buses in 20 AWG, 13 signal wires in 28-30 AWG to the Pi, the XT30, the IMU's 4 wires, tape and ties) is in `tools/mass_model.py`'s 3 % allowance, 11 g on this duck.

## The IMU

An Adafruit MPU-6050 (adafruit.com/product/3886, 26 x 17.8 x 4.6 mm, 1.8 g, I2C) taped flat on the chassis spine, behind the Pi's rail, on the Pi's 3.3 V and GPIO 2/3. Its axes: align them with the body's (X forward, Z up) and set the orientation in software.

## Centre of mass

Everything electronic is in the body: the Pi on edge in the middle, the battery and both regulators behind it with the header board on top, the IMU on the spine. `tools/checks.py` balances every pose with these masses where `spec/nano_duck.py` puts them, and passes; in single-leg stance the centre of mass is 0.7 cm outside the stance foot, as on every duck without ankle roll (the gait is dynamic).

## Not verified

- Every current is from a seller's page or an estimate; the Pi's 0.5 A is an allowance, not a measurement. Measure one servo at stall before trusting the split.
- pigpio's pulse steps are from its own documentation; no servo has been driven from this Pi.
- The Pi is fed on its 5 V pins, not its micro-USB: whatever protection that input has is skipped. Use keyed connectors throughout.
