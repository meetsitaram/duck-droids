# Matching a reference robot: what milli taught

milli (github.com/meetsitaram/duck-droids, 2026-11-02) is Pollen Robotics' microduck rebuilt on bigger servos: Feetech
STS3215s (the LeRobot SO-101 arm's servo) at the hips and knees, ROBOTIS XC330/XL330s at the ankles and head. The user
wanted "the looks of microduck for sure". It took the user about twenty corrections over eleven rounds in one day,
nearly all of them because the agent designed from reasoning and eyeballed pictures instead of measuring and copying
the reference. That is the main lesson: the user should not have to do this work. This file records the rounds, so
the next build starts where milli ended. Read it before a look-alike, and whenever the reference robot has a model
(URDF, MJCF, STEP, Onshape) you can open.

## The method, in order

1. **Get the reference's own model if it exists, and read it before drawing anything.** microduck's MJCF
   (pollen-robotics/microduck_rl) carried everything the rounds below fought to discover: joint positions, axes and
   ranges, which body each servo case rides in, where the Pi Zero sits, the thigh cover's outline, the shoe's layer
   thicknesses, the robot's own named poses. Respect the licence: microduck's code is Apache-2.0 but its meshes are
   CC BY-NC-SA 4.0, so milli measures them and copies none (no geometry, no meshes in the repo; renders local).
2. **Copy the joint layout first, the look second.** List every joint's position, axis and range, and every servo
   case's body and orientation (a script over the model; see "Tools" below). Lay out your joints the same way, then
   fit your actuators into that layout. In milli, nine rounds of layout-by-reasoning were replaced by one round of
   copying (round 9).
3. **Make your zero pose the reference's zero pose.** microduck's model stands at its zero pose with the thigh 58 deg
   back (a bird's leg). Building milli straight-legged and bending it for the pictures meant every servo case sat at
   an angle in the stance; with the stance as the zero pose, every case is square to the axes.
4. **Measure, don't draw.** For every visible part, slice the reference's meshes on a grid (5 mm steps: side profile,
   front outline, plan width, layer thicknesses), scale by the height ratio, and build from the numbers. Then compare
   close-ups on a grid (`tools/compare.py` writes 10 mm-grid head close-ups). "Did you even add a grid?" (the user,
   round 5) was the turning point.
5. **Find where the reference keeps its parts** (boards, battery, camera) in its parts list before packing your own.
   microduck's Pi Zero is in its head; putting milli's in the body made the body 22 mm too long (round 10).
6. **Validate by moving both robots the same way.** Apply the reference's own named poses (its keyframes) and
   single-joint moves to both, with matched axis signs, plant one foot, and compare where the joints end up
   (`tools/validate_poses.py`). Numbers that all move by the same amount mean the measurement is wrong (it read link
   frames, not points). milli's legs matched within 7 mm; the poses exposed three ranges too short (FOLD, neck back,
   head roll position) that no picture showed.
7. **Then build in Fusion** (step 7 of the workflow). The user asked "why would you build without CAD?" Answer: the
   spec is the CAD source; Fusion builds the checked geometry after the look is approved; rebuilding Fusion each of
   eleven rounds would have cost hours. Say so early, so the user knows when the CAD comes.

## Working with the user

- The user reviews by circling screenshots. Take each circle literally, find the cause, fix it, and send the same
  views back. Answer every mid-turn message in place, in a line, before continuing.
- When the user works remotely, send every review picture as a file (SendUserFile): they cannot open local paths.
- Every round: change the spec, `python -I spec/robot.py`, `python -I tools/checks.py` (0 failing), `python
  tools/compare.py`, `python tools/render_pose.py`, look at the pictures yourself before sending, then send.
- Ask the user only for real decisions (milli: the size trade-off, the servo split, cases on or off, Fusion now or
  later). Everything else, decide, do, and report the gap honestly (milli is 1.19x microduck's height, not 1.0x).

## The rounds

| # | User's words / what they flagged | What was wrong | How it was found | What fixed it |
|---|---|---|---|---|
| 0 | "microduck with feetech servos... the size of microduck"; Feetech legs, Dynamixel head; "not worth it to remove cases" | 15 STS3215s (55 g, 45 x 25 x 35 mm) cannot fit microduck's 6 cm legs | servo box from the SO-101 mesh (SO-ARM100, Apache-2.0); microduck's joint heights from its MJCF | STS3215 hips and knees (C044 1:191 / C046 1:147, scaled from the C001: "confirm before ordering"), XC330 ankles, XL330 head; cases as structure; Open Duck Mini v2's identified STS3215 damping/friction/armature |
| 1 | first side-by-side | 0.40 m tall; layout drawn by reasoning | `compare.py` beside microduck's model, scaled to the same height | targets as proportions (each microduck landmark x milli/microduck height, 10 %), height a warning |
| 3 | "looks nowhere near close" (face, hips circled) | flat face panel, centred eye, protruding bill; knee servo hung under the hip pitch servo: long spindly legs | Pollen's product photos | recessed face, thick ring eye; knee servo beside the hip pitch servo, under a white cover |
| 4 | "none of those have the mouth open, find more" | the jaw was guessed | the gallery has no open mouth; Pollen's launch video on X does (chatting 1:07-1:23, floor pick 0:45-0:52): mp4 from X's syndication JSON, frames local | U-shaped jaw under the face; floor-pick and chatting poses |
| 5 | "inner groove vs ours flat... sharp straight front... did you even add a grid?" | head drawn by eye: dome front, wrong slope, flat face patch | microduck's head meshes sliced on a grid | head built from the numbers; a loft along x (wider at the front than the back); leaning front plane; face = the hood's arch shrunk by the rim; 10 mm-grid close-ups |
| 6 | "that motor can tuck inside... side covers need work... neck needs improvement... the triangle is off angled... motor swing cover needs details" | neck servo bare in front of the body; L-shaped neck; thigh cover a blob on a human-style leg; jaw hinge tab wrong | photos; the thigh cover's outline unrotated from microduck's stance into the thigh frame | bird stance; cover = hull of three circles of 0.29 x thigh length (from the mesh); straight neck column, yaw servo inside the head; neck servo inside the body through a slot; jaw on side tabs at mid-head, driven by a rod (`remote_at`) |
| 7 | "one sided joints are bad, have them both sides"; "check how it nicely tucks in" (desk photo) | each servo held by its horn plate only | photo of folded microducks | U-brackets: horn one side, idler the other, bridged; the neck servo rides in the neck (`case_in='child'`); body notched so the neck folds 1.6 rad |
| 8 | "why so much space in between?"; "two side joints with extra details" | hip roll servo stacked over hip pitch: 64 mm of bare servos under the body | side view | roll beside pitch (later replaced, round 9); shoe ears both sides with hub and screws |
| 9 | "something is wrong with joint positioning... get the microduck urdf and check joints"; "why so much gap between legs and main body" | layout still reasoned, not copied | a script listing microduck's joints and every servo case by body | leg rebuilt on microduck's layout: roll servo standing under the yaw servo, horn forward; pitch at the roll axis' height, out on the roll bracket, its servo lying in the thigh; knee servo upright in the thigh's back; zero pose = microduck's stance; gap closed; 0.312 m |
| 10 | "our neck is a bit forward... the box is also big, do we need that?"; "legs are not that cute" | Pi Zero behind the battery; body wrapped past the neck; flat slab feet | microduck's parts list (Pi Zero in its head) | Pi to the head; body 98 mm (microduck 96 at scale); chunky shoe |
| 11 | "feet need slight curves on the bottom"; "compare" (two crops); "our orange layer is still thicker" | stacked slabs; orange 10 mm vs microduck's 6 | microduck's foot meshes: sole 12.9 mm, upper 6 mm | one outline for sole and upper, sole curling up underneath, servo in a pocket; sole 15.4 mm, upper 7 |
| V | "build it; start validating the joints by moving microduck" | ranges short of microduck's: FOLD (hip/knee 90 deg), neck back 60 deg, head roll joint in front of the yaw axis | `tools/validate_poses.py` with microduck's STAND/SIT/FOLD keyframes and single-joint moves | open (next round): widen hip/knee fold and neck back; move the head roll servo behind the yaw axis |

## Design traps specific to servo-built small robots

- **Servo cases are boxes with an off-centre shaft.** Model each case as a box with the shaft `shaft_x` from its
  middle (STS3215: 12.5 mm), the horn on the joint axis, the case in the parent (or the child: `case_in`). Every
  clearance follows from the case's reach round the axis (STS3215: 37 mm to its far corners, 16 mm on the short side).
- **Map where a case's long end sweeps** over the joint's range before placing any bracket near it: milli's thigh
  bridge went front-below the hip because the case swept 144-285 deg round the axis.
- **A U-bracket's bridge must clear the servo it wraps**: outside its swept circle, or in the sector its long end
  never visits.
- **A cover over a moving part needs a slot or a cut**, and a cut through a mirrored shell must be mirrored too (its
  `targets` renamed).
- **Height comes from stacking.** Look for axes the reference puts at one height (microduck's hip roll and pitch) and
  servos it lays flat; each stacked servo costs 25-45 mm.
- **Static one-leg balance is impossible without ankle roll** (microduck has none): single-support poses check
  torque and collisions, and report balance as a warning.
- **Scale knock-ons.** Shrinking the head left a bracket with crossed ends (negative size: the skin check's rejection
  sampling then hung for 10 minutes) and a band opening wider than the head's back. Tie dimensions to the shape they
  sit in, and re-run the checks after any scale change.

## Tools milli added (in the spec and `tools/`)

- `plate(name, y0, t, circles)`: a flat side-view outline (the convex hull of circles) extruded in y: thigh covers,
  jaw tabs, shoe ears.
- `loft(..., along='x')`: front-view sections stacked from back to front: a head wider at the front than the back.
- `joint(..., case_in='child')`: the servo case rides in the child, its horn on the parent's bracket (microduck's neck
  and hip pitch). `joint(..., remote_at=(x, y, z))`: the servo off the joint axis, driving it through a rod.
- `tools/compare.py`: the reference's own model rendered beside yours at one scale, plus 10 mm-grid head close-ups.
- `tools/validate_poses.py`: the reference's keyframes and single-joint moves on both robots, a joint-position table
  and side-by-side pictures.
- Snippets for reading a reference model (joints, bodies, servo cases, mesh slices on a grid) are in this session's
  history; turn the ones you reuse into tools.

## Practical notes

- Shell heredocs with nested quotes break in Git Bash: write patch scripts to a short temp path and run them.
- Python cannot open the session scratchpad's long path on Windows: use a short temp folder.
- Checks that suddenly take ten minutes usually mean a geom with zero or negative size.
- Videos on X: the syndication endpoint (`cdn.syndication.twimg.com/tweet-result?id=...&token=...`) lists the mp4;
  OpenCV reads frames when ffmpeg is missing. Keep the clip and frames local (`reports/compare/` is ignored).
