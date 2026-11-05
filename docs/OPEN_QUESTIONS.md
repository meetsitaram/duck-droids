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
| Big | RS03 mounting: only 4 rear holes are free, as RobStride's own screws fill the other 4, and they carry about 14 kg of head. The 8 front holes are free but need a new flange. The big duck's worker is trying the front holes |
| Big | Delete the old `big assembly` document in the Fusion hub, now that `big assembly real` replaces it? |
| All Feetech | Bench-test one STS3215 at a full 8.4 V before fitting? Sellers disagree on whether the 7.4 V servo takes it |
| All Feetech | A fuse at the XT30? To decide once walking current is measured |

## Measure on the first parts

- **Big:** the RS04's mass (no file gives one; sellers say 1.42 and 1.5 kg), each CAN bus's terminators (measure between H and L with the power off), and walking current on a current-limited supply before any pack goes near an actuator.
- **Small ducks:** walking current. The race-to-bracket clashes are mostly the drawn press fit, so check that a race seats on the first printed joint.
