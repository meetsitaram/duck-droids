---
name: humanoid-from-spec
description: Design and build a humanoid robot, or a look-alike of a reference robot, from one Python spec, the way the echo Figure 03 replica was built. Proportions come from reference photos and actuators are ones you can buy. The covers clear every joint, the offline physical checks are proven on broken designs, and the Fusion 360 model is built by script through MCP. Ends with a URDF/MJCF with bottom-up masses, a MuJoCo stand test, a retargeted motion-capture walk and a public repo with a README video. Use it whenever someone wants to design, model, replicate, re-proportion or iterate a humanoid or legged robot's mechanical design, including small hobby-servo robots (Feetech STS3215, Dynamixel) built to look like another robot (milli, a microduck look-alike). It also covers CAD or a URDF/MJCF for a robot they are designing, matching a robot's look from photos, video frames or the reference robot's own URDF/MJCF model, validating joints by posing both robots alike, and how echo and milli were built, even when they don't mention Fusion, a spec or this repo.
---

# Build a humanoid from one spec

This is the method behind echo (github.com/meetsitaram/echo). echo is a 1.727 m, 29-joint humanoid built to Figure 03's published
specs and look, with an Asimov 1-style internal layout and off-the-shelf RobStride actuators. Start from that repo:
its tools read `spec/robot.json` and work for any robot described the same way. "Make it yours" below lists what is
echo-specific. milli (github.com/meetsitaram/duck-droids), a 0.31 m microduck look-alike on Feetech STS3215 and ROBOTIS
XL330 servos, was forked from echo and added the method for matching a robot whose own model is available:
`references/matching-a-reference-robot.md`, round by round.

## How to use this skill

You (the agent) drive the work; the scripts only build, check and render. They cannot judge whether a shape looks
right or whether a trade-off is acceptable. You and the user do. So:

1. **Get oriented.** Read `LESSONS.md`, the spec (`spec/robot.py`), the last check report (`reports/checks.md`) and
   the comparison (`reports/compare/compare.md`). For a new robot, start at step 1 below.
2. **Agree the goal with the user.** Find out the target robot, what must match (specs, look, both), what may
   differ (payload, ranges), and what to change this round.
3. **Work in rounds** (see "Each round"): one change, the checks, before/after pictures beside the reference, then
   the user's review. Fusion, exports and publishing come after the user approves the look.
4. **Write down what you learn.** Every issue and its fix goes into `LESSONS.md`; every source into your sources
   list.

Stop and show the user pictures whenever the look is at stake; don't push to a public repo without their go-ahead.

## Eight rules, and why

1. **One source of truth.** Everything is generated from `spec/robot.py`: the Fusion model, the URDF/MJCF, masses,
   renders and the web viewer. Never hand-edit the CAD or `robot.json`. A change is then one edit and a rebuild, and
   the CAD, the simulation and the pictures cannot drift apart.
2. **Check before you build.** Fusion is slow: a full build is ~1,800 timeline features, and a link with many cuts
   takes minutes. The offline checks cover the whole robot in about 2.5 minutes. Make the spec pass, then build.
3. **Prove every check on a broken design.** A check that has never failed may not work. In echo, a cosmetic hip
   cover "connected" two parts after the bracket between them was deleted, and the check passed. Each check has a
   `--bad` case that must fail.
4. **Judge the look in pictures.** Every landmark was in tolerance while the hips read as a "boxy butt". Compare
   side by side at the same scale, from level views, in close-up crops, and from whatever angle the user looked from.
   Numbers hide ugly geometry.
5. **Real parts, honest numbers.** Use actuators someone sells, compute masses bottom-up from materials, and report
   the gap to the target rather than padding the model to hit it.
6. **Copy the reference's joints before its look** (milli). If the reference has a model (URDF, MJCF, STEP), read
   every joint's position, axis and range, and which body each actuator rides in, and lay yours out the same way;
   make your zero pose its zero pose. milli spent eight review rounds laying out joints by reasoning; one round of
   copying fixed what they could not.
7. **Measure, don't draw** (milli). Slice the reference's meshes (or measure its frames) on a grid and build every
   visible shape from the numbers; compare close-ups on a grid. Shapes drawn by eye came back "nowhere near close".
8. **Validate motion, not just poses** (milli). Move both robots through the reference's own poses and single-joint
   moves with matched axis signs and compare where the joints land (`tools/validate_poses.py`). It found ranges no
   picture showed.

## Before you start

- Fork echo, then read `LESSONS.md`. It lists every trap we hit with its fix; keep it open.
- Python 3.12 with numpy, scipy, trimesh, manifold3d, mujoco, Pillow, imageio and matplotlib; add mink for
  retargeting. Run scripts that read downloaded files with `python -I`. MuJoCo lives in user site-packages, so run the
  sim and render tools with plain `python`.
- Fusion 360, with its own MCP server turned on: Preferences > General > API > Fusion MCP Server (nothing to install;
  `references/fusion-mcp.md`). It is only needed for the CAD; everything else runs offline.
- On Windows, keep working files on short paths: Python cannot open paths over 260 characters.

## The stages

Work through these in order, and go back when a later one finds something: that is the point of them. Each ends in a gate you can show. A stage that cost us most when skipped is marked with what happened; `LESSONS.md` has the rest.

| # | Stage | What you leave with | The gate | What skipping it cost us |
|---|---|---|---|---|
| 1 | Idea and target | what must match, what may differ, references, a weight and size goal | the user agrees | |
| 2 | Off-the-shelf parts | every bought part: the maker's CAD and drawing, what's in the box, what the user already owns, where it's sold | each dimension traced to a source | a servo's datasheet size included its horn: 3 mm wrong on 5 joints |
| 3 | Architecture | joint order, what carries each joint, how each servo is held | both sides of every joint named, with a proven example | |
| 4 | Spec and offline checks | `spec/robot.py`, each check proven on a broken design | 0 failing | |
| 5 | The look | close-ups beside the reference | the user approves pictures, from close up | |
| 6 | Detail pass | connections, fits, strength, finish, parts and weight count | the list below, for every joint | a servo held at one end; plates in the air over the horn; 3,235 sharp edges |
| 7 | CAD model | the real parts in a generated model | interference explained, bodies match exports | |
| 8 | Prints and one real joint | printable parts from the model, one joint built | it moves, holds and doesn't flex in your hand | |
| 9 | Assembly guide | each part's real path and each screw's tool, as data, then animations | every path clear from outside the robot | |
| 10 | Simulation and motion | URDF/MJCF with real masses, stand, walk | sane numbers, sources written down | |
| 11 | Refine | one change at a time, back to the earliest stage it touches | re-check only what it touches | |
| 12 | Publish | repo, video, every number from a report | the user's go-ahead | |

### How to iterate without waiting

A full CAD build is the last check, not the test loop. Each of a day's rebuilds cost 15 minutes, for mistakes a one-minute test would have caught.

- **Prove each fix at the smallest scale that can show it:** a number from the spec, then one link in a scratch document, and only then the whole robot.
- **Test a risky change alone first:** a new fillet, a new way of placing a part.
- **Batch what's left** into one full build, and tell the user what it will and won't show.
- **Split the model** so that one change rebuilds one link (being tried: a document per link in an assembly).

### Saying something is fixed

Fixed means a check or a picture says so. For each thing the user asked, say which: a line from the spec, a check that passes (and failed on the broken design), a picture of that spot, or **not yet seen**. "It's in the code" isn't one of these: a fillet that was in the code was deleted every time, for two builds. Say so when you were wrong, and put the miss in these docs the same day.

## Stage 1: Idea and target

Write down the goal first: what it is for, what must match, what may differ, and a weight and part-count goal to hold each later stage to. A generated picture of a robot can suggest a look, but not a dimension, a mass or a mechanism: check what it shows before copying it.

### 1. Pin the target

Collect the published specs (height, mass, payload, battery, DOF) and the best reference pictures you can get from
the web.
- Open the maker's product page and reveal video in a browser you control.
- Seek the page's video player to exact times with JavaScript, enlarge it to fill the window and screenshot it. A
  canvas export fails on a cross-origin video.
- Keep the frames local, never in the repo: they are the maker's copyright.

`references/reference-images.md` has the code, how to choose frames, and how frames become numbers and loft
sections.

Write the targets to `spec/targets.json`: landmark heights (chin, shoulder top, elbow, wrist, fingertip, hip line,
knee) and widths, each with its source frame, time code and tolerance.

If the reference robot's model is published (its RL or simulation repo often has a URDF/MJCF with meshes), get it
first: measure landmarks, outlines and joint positions from it on a grid, check its licence (microduck's meshes are
CC BY-NC-SA: measure, never copy), and keep it outside the repo. When the robot cannot be your target's size (milli's
servos are bigger than microduck's), check proportions: each landmark scaled by your height over the reference's.
Look for its motions in the maker's launch video, not only its gallery (microduck's open mouth was only in the
video). See `references/matching-a-reference-robot.md`.

Measure heights in level views only; a raised camera lifts every top surface. For a 3/4 frame, fit the camera
angle first: render the model at several angles and keep the one whose silhouette widths match (echo's 3/4 frame
was at 60°, not 40°). Zoom into every region of the reference before modelling it. echo's "black head" turned out
to be a grey knit hood with a black visor, visible only in a close-up.

## Stage 2: Off-the-shelf parts

Before any layout. A bought part's real shape decides what can be built round it.

- Ask what the user already owns, and design for that first: it can make a build possible this week instead of in two months (their salvaged servos, their controller board).
- **Get the maker's own CAD for every bought part first,** from their site, or the user's own CAD library: ask. A robot's model of a part is simplified, and a datasheet's size may include the horn (the XL330's 26 mm does: a 3 mm error on 5 joints, found after the first build). Note where its connectors are, and what comes in the box.
- **Read the maker's page before asking anyone to measure.** A board's dimension drawing gave every hole and connector; retailer listings disagreed about the supply voltage, and its own silkscreen settled it (a 9-12.6 V board on a 7.4-8.4 V pack: say so, and bench test it).
- **Photographs show what no table does:** where sockets open, what's plastic and what's metal, the colours, which screws come in the bag. Use them for looks and for questions, and take numbers from drawings.
- **Look in the user's own CAD,** but stop looking when it stops paying: name what you didn't find, and carry on with room to spare.
- **Licences:** note where each model came from and what covers it, including a part inside someone else's repository (the repository's licence may not be the maker's). Keep the files out of the repo if unsure, and fetch them by script.
- **Actuators.** Put the catalog in `spec/actuators.json`: size, mass, rated and peak torque, gear, rotor inertia.
  Mark retailer numbers as "confirm before ordering". Hobby servos are boxes with an off-centre shaft: take the box
  from the maker's CAD (milli: SO-101's STS3215 mesh) and the response from someone's identification (Open Duck Mini's
  STS3215 numbers). Lower-ratio versions of one servo trade torque for speed (STS3215 C001/C044/C046).

## Stage 3: Architecture

### 2. Choose the architecture

- **Joints.** List the DOF and the order of each chain's joints. Borrow a proven layout from an open-source robot
  (Asimov 1, Unitree G1/H2, AgiBot X2): download their URDFs and compare joint order, offsets and ranges.
- **Before reordering joints for looks, check where the new first actuator goes.** A yaw-first hip needs a motor
  above each hip; echo had no room for one, so the hip covers were moved to another link instead.
- **With a reference model: copy its joint layout** (positions, axes, ranges, which link each actuator case rides
  in, which axes share a height), and take its zero pose as yours. Find where it keeps its boards and battery too
  (microduck's Pi Zero is in its head).
- **Hold every joint on both sides.** A servo held only by its horn plate flexes; give each a U-bracket (horn one side,
  idler the other, bridged clear of the case's swept reach), or a thin bearing round the horn, on the joint's axis, as
  microduck's (slice the reference through each joint's axis to see which). A post has to clear the case's corners whatever
  the range, so on a small robot it shows; a bearing never sweeps.
- **Calculate a mechanism before offering it, from the range the motion really uses.** Compare joint strength with robots of the same class, read from their own models, by weight x leg length.
- **Look for proven examples before picking a mechanism.** A neat calculation isn't evidence. Search for who has used that drive, bearing or material at this size and load, and name them when proposing it. If none turn up, say so, as it's a warning sign and the user's call. (A roller-chain knee on a large robot passed its torque numbers; a search only found chain on small robots, with larger machines using linkages, cables or belts. Search again when the size changes: what works at one scale may have no precedent at another.)
- **Torque.** Size each joint with the task poses in step 4, not by feel. Trade capability for looks only knowingly
  and with the user: echo took smaller elbow motors to match Figure's arms, at 3 kg continuous instead of 20.
- **Credit references.** Note the licence of every robot you borrow from. Asimov 1 is CERN-OHL-S-2.0 hardware and
  GPL-2.0 software. echo follows its layout but copies none of its files.

## Stage 4: Spec and offline checks

### 3. Write the spec

`spec/robot.py` holds:
- anchor heights at the top (hip, knee, ankle, shoulder, elbow, wrist, hem, neck, chin);
- links made of primitives, each with a role (cover, rigid part, actuator, decal, linkage, cut);
- joints with actuator, range and output side;
- materials.

Write the left side once; the right is mirrored. Actuator stators go in the parent link automatically, and an output
flange on the child.

Place every part relative to the anchors, so re-proportioning is a few numbers. Leave a comment with the reason for
each iteration's numbers next to them; it is the design's memory. See `references/spec-patterns.md`.

### 4. Run the checks until 0 failing

```bash
python -I spec/robot.py
```

```bash
python -I tools/checks.py
```

The checks cover:
- the targets and a bottom-up mass;
- actuators on their axes, and no rigid part inside another;
- covers clear of motors, structure that holds together, internals hidden;
- every joint swept from minimum to maximum, covers included;
- task poses: torque against rated and peak with a 1.5 margin, balance over the feet, limits after balancing, and
  collisions.

Fix the design, not the check. When you add a check, add a `--bad` case for it and watch it fail. See
`references/checks.md`.

## Stage 5: The look

### 5. Look at it

```bash
python tools/render_pose.py --views
```

```bash
python -I tools/compare.py
```

These render the spec offline and put it beside the reference frames, at the same height, with the target lines
drawn across both, plus close-up crops of each region. For every change, render before and after side by side from
front, side, back, 3/4 and the user's own angle.

To find gaps that let light through, render on a green background: green inside the outline is light through a gap.

With a reference model, `tools/compare.py` renders it beside yours at one scale (front, side, 3/4) with its landmark
lines, plus 10 mm-grid close-ups; then `tools/validate_poses.py` poses both robots alike (step 8 rule).

## Stage 6: Detail pass

Do this before the CAD model and again after it. Go joint by joint, and ask the questions a person holding the part would ask: what holds this side? Where does the plug go? Where would it snap?

- **Screws:** plastic round each hole (EDGE); a part's holes no nearer its edge than 2 perimeters for a clearance hole, 3 for a pilot. Every screw in the spec, those that come with a bought part too. On the finished robot, for each screw: what has to come off to reach it? Leave a way to the ones you'll need again, like a hole over a horn's centre screw.
- **Close-ups of every visible part, every round, looked at before the user sees them:** checks ask whether things fit and hold, not whether they look clean. `build.look_check()` lists tiny flat faces, which is where shapes that don't quite meet leave a step; the picture decides. Where two shapes join, make their outlines run into each other. Cutting one part away exposes the joins behind it, so look again. A clearance swept wider than the real motion is a visible flaw too: sweep the range the joint has, in the direction it goes.
- **Why is each servo where it is?** Compare each with the reference's model, by its shaft against its joint. Prefer a horn on the joint to any linkage. Before saying a design is the reference's, open the file.
- **Shells:** whatever a shell gives way to must stay inside it, clearance included (PIERCE).
- **Each small part:** what does it do? If its neighbour already does that, it goes.
- **The reference's own model:** open its parts list and place each of yours beside it (microduck's speaker, battery and two-part shells were there to read). Measure how proud each visible part stands: use the reference's numbers rather than a clearance constant.
- **Connections:** each servo screwed at both ends, or the reason it isn't (ENDS). Each plate seated on the real horn (SEAT). A stand-in drawn at real size, even when it shows a gap. A bearing seat's wall whole: who gives way depends on what a part does.
- **Connectors:** the sockets on every board and servo, the plug, its wires and their way out; power reachable; a chain's end servo needs one lead, its middle ones two.
- **Mounts:** a board's real holes, what its standoffs and nuts are, and which side a tool reaches each screw from.
- **Strength:** the load path through each joint, sideways loads as well as the weight. Beam estimates have no corners in them: a sharp inside corner multiplies stress 2-3 x. Add gussets or a curved arm, and say a check can't prove it. Ask whether anything peels: a lid held only at its far end, say. Offer metal for what printing won't carry.
- **Finish:** join, then round, then cut pockets. Size the radius to the part. Outside edges only, nothing a servo or a bearing fits against. Curved shells, with the inside curved too. Screws in a colour you can tell apart.
- **Weight and count:** grams, parts and screws per joint, each screw at its real mass. Remove what isn't structural or needed for fit before thinning walls: thinner PLA comes last.

### 6. Give every joint room

Rigid covers are where a humanoid design gets hard. For each joint, decide which link each cover rides on and what
moves against it. Make every interface round about the axis that moves it, or a plane square to that axis. Use a
sphere where several axes cross; spheres also hide seams. The patterns, with numbers, are in
`references/joint-covers.md`: openings, hinges, cups, sockets, the multi-axis hip, pads and the sock-shoe.

## Stage 7: CAD model

### 7. Build it in Fusion

Real parts in it, not boxes: the maker's models, each piece moving with the link it belongs to, coloured from product photos. Their interference report is the best fit check there is: read it, after filtering a model's own overlaps, and check what a STEP file includes (one came with a horn the servo doesn't have). Round parts here, and print from these bodies.

Build after the user approves the look and the pose validation passes; tell the user early that the spec is the
CAD source and Fusion comes then (milli's user asked "why would you build without CAD?"). **Build earlier than feels
necessary: the CAD finds what the offline checks can't.** milli's first build found 143 clashes and shells full of
holes behind 950 passing checks.

Regenerate `spec/parts.json` (`tools/export_prints.py`), build every link in a new document with no timeline, turn the
timeline on, add the joints, then check: `build.status()`, `build.verify()`, `tools/verify_fusion.py` (point by point against the
STLs) and Fusion's own `analyzeInterference`, explaining every clash left. Then look at it, from every side, the top and
underneath, and chase every odd line: nothing else finds a slit in a cover. Save only when the user says. See
`references/fusion-mcp.md`. If the viewport cannot save images, the offline renders are the same shapes, but that
is not the same check.

## Stage 8: Prints and one real joint

Export from the CAD bodies, so that what you print is what you looked at. **Measure the exported STLs against the real parts:** a model can pass every fit check because a bought part's solid was fused into the print (BOUGHT). One STL is one colour unless a note says how to print it (COLOUR). Print one joint, the most loaded one, and build it with real parts before buying the rest: push on it by hand, feel for flex, check the plugs go in. No check here replaces this. (Others building ducks found leg flex only on the real thing, and added bearings everywhere.)

## Stage 9: Assembly guide

The build order is data (`tools/assembly.py`): each part, its path, each screw. The guide and its animations are rendered from that data, so a part can't be shown arriving by a way that no check has passed.

- **A path starts in clear space,** not 20 mm away, and goes round things if it must: a straight line can hide an impossible move.
- **Real tools and hands:** the driver a screw needs (self-tapping screws take a Phillips, not a hex key), and fingers holding the part.
- **Wires are parts** once plugged in: they can block the next step.
- **Service, not only assembly:** on the finished robot, list what must come off to reach each screw, connector, and the battery and charge port. A check that only asks at the moment of fitting can't see this.
- **Real shapes:** run it with the maker's models, not boxes.
- **Videos:** the reveal and the build video have their rules in `references/assembly-videos.md`. Read them before rendering. Filming the build is a review: this round it found a two-colour part, and auditing that found a bearing that couldn't fit.
- Expect this stage to find more issues, and go back.

## Stage 10: Simulation and motion

### 8. Robot files and physics

```bash
python -I tools/make_robot_files.py
```

```bash
python tools/sim_stand.py
```

These write the URDF and the MuJoCo model, with masses and inertias from materials and joint armature, damping and
friction from the actuators. The robot must then stand and squat to 90° knees and back in MuJoCo, every joint limited
to its peak torque, with little tilt and no saturation.

### 9. Motion

Retarget a human capture (echo used a PICO full-body suit) to the joints with IK, locking planted feet. Play it back
kinematically for videos and the web viewer. Replay it through the collision test, which catches the combined joint
motions that single-joint sweeps cannot. See `references/motion-and-publishing.md`.

## Stage 11: Refine

One change at a time, starting at the earliest stage it touches, re-checking only what it touches. Then the checks and a close-up of that spot, then the user. "Each round" below is the list. Every issue and its fix goes into `LESSONS.md` and, if it's a kind of miss, here, the day it happens.

## Stage 12: Publish

### 10. Review, publish, record

Put the new model in a review page (the web viewer, with movies and renders) and wait for the user's go-ahead.
Then commit and push, with the README video re-rendered and every quoted number copied from the reports. Add a
`LESSONS.md` row for each issue the round hit and how it was fixed. Never publish the reference robot's frames,
panels made from them, raw motion captures or anyone's trademark.

## Before you call it buildable

Stages 2, 6, 7, 8 and 9 in full, as a list. Checks that pass mean only what they test. Collision and fit checks say nothing about whether a part can be printed, or holds. Say so to the user, and before a design counts as ready, have these:

- **Bought parts at their real shape:** sections of the maker's mesh, not a bounding box (steps, bosses and lumps change what a seat can be), seen from all 6 sides. **What plugs into them is part of them:** cable sockets are on a face, the plug and its wires need room, and the wires need a way out.
- **Every screw in the spec:** size, length, position, direction, and the room its head takes. Parts held by nothing show up. So do parts held by screws on one axis, which turn about them (HOLD).
- **The look is a requirement, and something measures it.** Compare with the reference at close range, not only in overview pictures. Count sharp edges on the finished bodies (`build.look_check()`). Round the joined part, sized to the part (a big cover several mm, its inside too), before cutting pockets, so fits stay crisp; reject a fillet that loses over 3 %. Print from the bodies that have those fillets.
- **The maker's CAD in the model for every bought part,** moving with the link it belongs to (a horn with its child), and Fusion's interference check run against it, after filtering a model's own overlaps. Stand-ins at real size: a part drawn big enough to reach its neighbour hides a gap.
- **Each servo held at both ends of its case, and each plate seated on the real horn** (ENDS, SEAT in `tools/assembly.py`).
- **Count parts, screws and grams per joint** in each design review, and each screw's mass in the mass model.
- **Every servo drives something:** a horn on the child, or a linkage solved and swept through its range (DRIVE). A joint can pass every check with nothing driving it.
- **Printed parts checked against each other, as exported:** a link is not one solid to a printer. Say who gives way, cut real pockets with clearance, and check the exports (MATE, APART, SKIN in `tools/printable.py` and `tools/assembly.py`). A check that skips parts of one link can't see any of this.
- **Printing, per part:** the orientation with the least overhang, what needs support, a sealed void, holes big enough to print (`tools/printable.py`). Exported already turned that way, left and right.
- **The build order as data**, with paths: each part slides in without cutting what's already on; a key reaches each screw at that moment; the thread bites something; the head clamps something (milli's `tools/assembly.py`).
- **Per printed part, not per link:** one piece without bought parts in it; walls at the printer's minimum; fits the bed; exported with its holes, hollow where it is hollow (`tools/buildable.py`, `tools/export_prints.py`).
- **A load estimate through each section on the load path**, at a landing's load, against the material across its layers. A hand estimate finds weak parts; it doesn't replace FEA or a test.
- **Limits scaled to the robot:** a volume limit from a 1.7 m robot hides real collisions on a 0.3 m one.
- **Sim results sanity-checked:** the floor carries the weight, the whole robot collides, inherited tools have really run on this robot, each joint's speed is under its actuator's, and every sim parameter's source (measured, scaled, copied, guessed) is written down.
- **Electronics are real parts with links:** each board's size from its listing, in a place checked against everything that moves; every rail's stall current against its regulator; the pack's full voltage against each part; every connector against its current; signals and power routed through the joints (`docs/WIRING.md`).
- **The parts list re-read at the shop when you finish, not from memory:** stock against the quantity, and what the page says is NOT in the box. Say which entries you couldn't re-read. Name what's on order the longest: it sets the date.
- **The CAD model built, and compared with the exports.** Offline solids aren't the printer's solids until something has checked.
- **One joint printed and assembled** with real parts before buying the rest. **None of the checks above replaces this.**

Each of these has a `--bad` case. When a look-alike's reference does something odd, check that before "fixing" it.

## Each round

1. Change `spec/robot.py`, with the reason in a comment.
2. `python -I spec/robot.py`, then `python -I tools/checks.py`: 0 failing.
3. Render before/after from front, side, back, 3/4 and the user's angle; `compare.py` against the reference;
   a green-background render if any seam changed.
4. `python -I tools/motion_collisions.py` if a joint or cover changed.
5. Show the user the pictures and agree the change. Look at them yourself first; when the user is remote, send
   them as files. Take every circle on their screenshots literally.
6. Rebuild the changed links in Fusion, rebuild their joints, check `status()`, save, then export STEP, `.f3d` and
   STLs.
7. `make_robot_files.py`, `sim_stand.py`, `mass_model.py`, the README video and views, and the web viewer export.
8. Update the README numbers from the reports; add the `LESSONS.md` rows; review page; commit; push after the
   go-ahead.

## Make it yours

The tools are generic, but some parts are echo's. Change these for a different robot:
- `spec/targets.json` and `measure()` in `tools/checks.py`: your landmarks and how to measure them on the model;
- `POSES` in `tools/checks.py`: your task poses and payloads;
- `PAIRS`, `FRAME_BOX` and `BANDS` in `tools/compare.py`: your reference frames and the regions to crop;
- the leg and arm name keys in `tools/checks.py` and `tools/motion_collisions.py` (`hip`, `knee`, ...);
- `tools/ik/pico_to_echo.json`: body names for retargeting;
- `NAME` in `tools/make_robot_files.py` and `DOC` in `cad/fusion/build.py`;
- the anchors and every link in `spec/robot.py`;
- `MAP` and `MARKS` in `tools/validate_poses.py`: the reference's joint names and the landmarks to compare.

## Reference files

- `references/reference-images.md`: getting reference images from the web (video frames at exact times, stills),
  choosing frames that measure well, and turning them into targets, anchors and loft sections. Read before the
  first measurement.
- `references/spec-patterns.md`: how to write links, joints, covers, cuts and materials. Read before writing or
  changing the spec.
- `references/joint-covers.md`: the joint and cover patterns. Read when a joint collides, a cover shows a gap or
  light, or a joint looks wrong.
- `references/checks.md`: what each check guards, its thresholds, and how to add one. Read when a check fails or
  you add one.
- `references/fusion-mcp.md`: driving Fusion through MCP: build, status, save, export, memory. Read before the
  session's first Fusion call.
- `references/motion-and-publishing.md`: retargeting, videos, the web viewer and the walk collision replay, plus repo
  hygiene, licences and the README. Read when making motion or publishing.
- `references/assembly-videos.md`: the rules for reveal and build videos: portrait, no hands, contrast, labels and their
  place, grouping screws, what to check before sending. Read before rendering any assembly video.
- `references/sources.md`: every reference echo was built from: target specs and frames, robot URDFs, parts data,
  code and tools, what each was used for, and what its licence asks. Read before you borrow anything, and
  start your own list on day one.
- `references/matching-a-reference-robot.md`: milli's review rounds (about twenty user corrections: what the user
  flagged, the cause, the fix), the method they add up to (copy the reference's joints, measure on a grid, validate by posing both), traps of
  servo-built small robots, and the tools milli added. Read before any look-alike, and whenever the reference has a
  model you can open.
- `LESSONS.md` at the repo root: the traps, with what fixed each.
