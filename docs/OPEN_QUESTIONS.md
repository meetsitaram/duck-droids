# Open questions

Questions that still need an answer, from a measurement, a maker or you. Where one had to be settled to keep designing, the choice made is written here, so it can be reviewed later.

## Chosen for now, to review

| Duck | Question | Chosen | Why | How to settle it |
|---|---|---|---|---|
| Big | How deep is the RS04's M5 output thread: 3.5 or 6.5 mm? | **3.5 mm.** About 3 mm of thread engaged, never reaching the bottom, and the 3 dowel pins carry the torque | It's what RobStride's STEP file shows (blind at z +22 mm). 6.5 mm is the distance from the floor to the pin tips, the figure the spec had. Designing for the shallower hole is safe if the real one is deeper, but not the other way round | Measure a real RS04 with a depth gauge, or ask RobStride. If it's 6.5 mm, longer screws can be used. If it's 3.5 mm, ask what the screws and pins are each rated for. 9 M5 screws with under 4 turns each are weak in pull-out |
| Hybrid | The head's servos at 5 V through a UBEC, or straight from 2S? | **5 V** | Inside ROBOTIS's 6 V limit, and the parts and model are already built this way | Bench-test one XL330 and one XC330 on a full 2S against 5 V, for temperature and life. See [WIRING.md](WIRING.md#todo-review-the-heads-voltage) |

## Waiting for you

| Duck | Question |
|---|---|
| Big | Many frame joints are M4 screws tapped into the edge of 8 mm plate: the hip pitch bridge, head pitch yokes, head roll cradle, head rails, beak mount and tray, shin top. Accept them, or go to angle brackets or thicker plate? Nothing has checked their strength |
| Big | The shin is a 5 mm 6061 tube with one welded seam. Accept a weld there? |
| Big | The hip roll yoke and its standoff ring are one machined billet part, as there's no room for screws. Acceptable to machine? |
| Big | 14 of the 22 actuator harnesses don't reach the boards on the deck: even the shortest route past the hips needs about 420 mm against 350. A CAN hub and power block in each leg, or extension cables? See [CABLES.md](big/CABLES.md) |
| Big | The knee's two RS04s each drive their own crank and rod into one lever: two linkages constrain the joint twice, and unequal rods preload each other. Keep it with adjustable rods, put both RS04s on one crank shaft with one rod, or rebuild the hip roll and pitch as a differential? See [PAIRED_ACTUATORS.md](big/PAIRED_ACTUATORS.md) |
| Big | Paired actuators' control: one joint controller, torque split between the pair, a small anti-backlash bias, a joint calibration and fault check at start. Designed in [PAIRED_ACTUATORS.md](big/PAIRED_ACTUATORS.md), not written or tested. Read Robertz et al. (ICRA 2010) in full before citing its figures |
| Big | Delete the old `big assembly` document in the Fusion hub, now that `big assembly real` replaces it? |
| All Feetech | Bench-test one STS3215 at a full 8.4 V before fitting? Sellers disagree on whether the 7.4 V servo takes it |
| All Feetech | A fuse at the XT30? To decide once walking current is measured |

## Settled

- **Big, RS03 mounting:** each RS03 now uses its 8 free front holes, through a 6 mm ring with countersunk M4 screws, as well as the 4 rear ones.

## Measure on the first parts

- **Big:** the RS04's mass (no file gives one; sellers say 1.42 and 1.5 kg), each CAN bus's terminators (measure between H and L with the power off), and walking current on a current-limited supply before any pack goes near an actuator.
- **Small ducks:** walking current. The race-to-bracket clashes are mostly the drawn press fit, so check that a race seats on the first printed joint.
