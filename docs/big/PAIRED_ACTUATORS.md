# Two actuators on one joint

The big duck drives its hip roll, hip pitch and knee with a pair of RS04s each. Nothing here is built or tested, and no control code for it is written. This is the design to review.

## Why pair them

One RS04 gives 120 N m peak, and the spec gives the hips and knees 240 N m for a 98 kg duck. A pair on one axis, either side of the part it turns, doubles the torque and puts no bending moment on either output.

## Is it done elsewhere

- **Yes, for two motors on one axis, outside humanoids.** Robertz et al., *Precise robot motions using dual motor control*, ICRA 2010 (Lund): two motors drive one linear axis through two pinions on one rack. A master runs position control, and a slave runs torque control. At low load the slave pushes slightly against the master, so both gear trains stay in mesh and backlash goes away. Under load both push the same way. The summary we read reports backlash down by over 96 % on their test cart. Industrial gantries and rotary tables use the same master and slave scheme. **Read the paper in full before citing its numbers: only its figures and a summary have been read.**
- **Humanoids mostly pair motors as a differential instead:** two motors drive two joints, and each motor helps both. ToddlerBot's waist does this, with two motors on yaw and roll through coupled bevel gears (arXiv 2502.00893, read from the paper). It is not two motors on one axis: every other ToddlerBot joint has one motor.
- **Not found:** a humanoid with two redundant pushrods on one knee, as the big duck's knee has now.

## How a pair is driven

Two position loops on one shaft would fight: each motor pushes toward its own idea of the angle, with a torque of about its stiffness times the difference. At 150 N m/rad each, 0.5 degrees of mismatched zero is about 1.3 N m of steady fight, which is only heat. A wrong sign is the full 240 N m against itself.

1. **One controller per joint.** The Pi computes the joint's torque from one angle, the mean of the two encoders: tau = kp (q* - q) + kd (qd* - qd).
2. **Each motor gets a share, in torque only.** RobStride's MIT mode with the motor's own kp and kd at 0, so it adds only the torque it's sent. Both are on one CAN bus and get their commands in the same cycle, at 500 Hz to 1 kHz. This is what the simulation already does: one joint with twice the torque.
3. **A small opposing bias near zero load,** faded out as the load rises, as in the Lund paper. Each RS04 has a planetary gearbox inside, so each has backlash; the bias keeps both in mesh. It costs steady heat: size it on the bench.
4. **Calibrate the pair together,** once, on the assembled joint: record both encoders at a reference pose and keep the offset. At every start, check that the two readings agree within about 0.2 degrees, and check each motor's direction with a small nudge while its partner is unpowered.
5. **Watch them run.** Both should draw nearly the same current. A steady difference is preload or a calibration fault.
6. **If one faults,** drops off the bus or overheats, put the other in damping only, not holding, and stop the walk.

## The knee is the weak part

Each knee RS04 drives the knee through its own crank, rod and lever. Two linkages on one lever constrain it twice: any difference in rod length becomes a preload that no software removes, and each crank's share changes along the stroke (1.54:1 to 2.56:1). If it stays this way, the rods need threaded, adjustable ends, set at assembly for no preload at mid-stroke, and each crank's torque is tau_knee / (2 x ratio(q)).

**To decide** (see [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md)):

- Both knee RS04s on one common crank shaft with one rod, so the knee becomes a rigid pair like the hips.
- Or the hip roll and pitch rebuilt as a differential: the same four RS04s, each helping both joints, as humanoids usually do.

## References

- S. G. Robertz et al.: *Precise robot motions using dual motor control*, ICRA 2010 (Lund University).
- ToddlerBot: arXiv 2502.00893, Sec. 3.2 (waist).
- US 8686680 B2, *Dual-motor series elastic actuator*: a joint controller gives one torque, split between two motors with an opposing preload. Read as a summary only.
