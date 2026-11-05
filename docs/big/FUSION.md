# Big duck in Fusion

**NOT SAFE TO BUILD.** A model that builds in Fusion says nothing about strength. Clash checks test whether shapes overlap, not whether a frame holds: see [Open before ordering](BOM.md#open-before-ordering). Fit is what this page checked. Strength wasn't checked at all.

![The big duck in Fusion, three-quarter](../images/fusion/big/34.png)

The actuators are now RobStride's own models. Those files have no licence, so they stay on this machine, in `%TEMP%/figrefs/robstride` (`python -I tools/fetch_servo_cad.py`), and in the private hub documents in my-projects / duck-droids / big. They're not in the repo, and there's no `cad/duck-droids-big` export.

## What the files say

Read in Fusion, by its bounding box and point-in-solid scans, and from the files' own circles. All in mm, and each file says mm. In each, the axis is z through the origin. The RS04's output faces +z; the RS03's and RS00's face -z. No file holds a mass, so 1.42 kg can't be checked. The numbers are in `RS` in `spec/big_duck.py`.

| RS04 | Spec had, or manual says | The file |
|---|---|---|
| Overall | a 120 x 56 cylinder | 120 x 55.7, z -27.2 to +28.5 |
| Case | | 120 across, z -14 to +25, 39 long, as the manual says |
| Rear step | manual: 94 x 13.2 | 94 x 13.2, as the manual says. A flat and a slot in it |
| Output face | manual: 0.5 past the stator | a ring r 12.5-25 at z +25.5, 0.5 past the stator's face (r 30.25-60) at +25 |
| Pins | manual: 3 x 6 on 35.86, standing 3.3 | 3 x 6 on 35.86, tips at 28.5: **standing 3.0** |
| Output screws | M5 x 9 on 36; manual: **6.5 deep** | M5 x 9 on 36, 12 places less the 3 pins' (not 9 equal). **Blind at z +22: 3.5 deep.** 6.5 is floor to pin tip |
| Mount screws | 10 M4 on 106, 5 and 6 deep | 10 M4 on 106: 7 deep at the front (5 by the manual) and 6 at the shoulder |
| Cable | "out of the side of the rear step" | a 7.3 sleeve, radial, angle 75, z -20.3, ending at r 58.1 |

| RS03 | Spec had | The file |
|---|---|---|
| Overall | a 106 x 56 cylinder | 56.6 long. Body 92.8 across, 8 lobes to 106.6 |
| Rear step | none | 79.5 across, 14.6 long, from z 42 |
| Output | | r 35, 2.5 past the stator |
| Mount screws | 8 M4 on 98 | 8 M4 on 98 at the front. **Only 4 free at the rear:** RobStride's own cap screws fill the other 4, standing 4 mm past the face |
| Output screws | 6 M4 on 30.36, 6 deep | 6 M4 on 30.36, 9 deep |
| Pins | 3 x 4 holes | 3 x 4 holes, 7 deep: no pins of its own |
| Plugs | not read | on the rear step's sides, at z 53, facing +-x |

**RS00:** 57 x 52.1, one piece with its 2 sockets. Its mount is drawn but its beak drive isn't designed.

The power board and hub: [wiring](WIRING.md#the-boards-from-their-step-files).

## What changed in the design

- **Every stator hangs by its shoulder.** Plates that lay on a rear face had nothing flat to lie on. A plate now sits on the 13.2 mm step's shoulder, with a 95 mm bore, 10 M4 x 12 and a closed window for the cable. The step stands 5.2 mm past the plate. So the leg's outer plates moved in 16.7 mm, and thigh covers stand 15 mm off them, for the cable.
- **Stators turn to match the plates.** Each cable points along an axis. Both hole patterns are symmetric about the cable, so a right-hand actuator, turned 180 deg about its cable, has its holes where the left's mirror lands. Fusion places them that way: rotation only, never a mirror. The rotor's zero is set in software to suit.
- **The hip yaw is new.** It was a bearing round the case's own 120 mm, on a sleeve the case left no room for. Now a fixed housing hangs from the deck round the stator, holding the bearing's outer ring below it. The inner ring is on the output's flange. The leg's moment goes housing to deck, and only torque goes through the actuator. Its cable comes out above the deck, in the body.
- **Every output has a flange**, with holes for pins and counterbored screws sized to engage 3 mm of thread: M5 x 8 on the cranks, x 10 on hip pitch (low heads) and ankle, x 12 on hip yaw and neck, x 18 on the roll yoke, which is hollow so a key can reach them. Plates bolt to flanges by a second circle of screws, so they go in after: 16 mm screws fit in the thigh's 24 mm. The hip pitch's old M5 x 16 through 20.5, the ankle's x 20 through 20, the roll's 8 deep into 6.5 and the yaw's heads in a 2 mm gap are gone.
- **The knee's four-bar didn't close.** Giving the rods their motion showed it: at 106 mm the rod can't reach below knee -0.74, probably since the hip moved after that sweep: a comment still had it 40 mm lower. Now the same crank and lever, with a 148 mm rod and the lever at 150 deg, closes from -0.92 to +0.30. Ratio: 1.54 at its weakest and 1.89 bent, as before; 2.56 at the straight end, not 3.35. The walks use the first two.
- **Rods have holes and bushes**, 14 x 10, on 10 mm pins, and cranks and rods are their own parts.
- **RS03s.** Each rear plate has 4 screws and 4 clearance holes for RobStride's cap screws. The bridge and cradle moved 14 mm, as its output is nearer its shoulder than the old cylinder's end, so the head didn't move.
- **Smaller:** the hip roll cheeks are wider, 132 mm, as a 110 mm plate left 2 mm beside its screws. Front body posts moved off the yaw stators' steps. The computer's box stands 6 mm off the deck, over them. The neck spine has a window for its screws' key. Head pitch shaft, knee shaft and pins have bores.

## The closed loop

The knee's four-bar can't be a tree of joints, and the trainer's model needs a tree. So the spec keeps one knee joint. Its cranks and rods are drawn in the thigh's link at knee 0, tagged with a `group`, and `spec['mech']` holds their joints and their angles at 13 knee angles. In the Fusion assembly each is its own part, on a revolute joint: crank to thigh, rod to crank. **The rod's far end isn't jointed to the lever, so Fusion's model doesn't drive the knee.** Moving the knee there leaves the rods behind.

What checks that it closes is `tools/big_sweep.py`, offline, on the spec's stepped shapes: left knee, 13 angles, cranks and rods against the thigh, shin and each other: 0 clashes. Flip the rod's angle and it reports 10, so it can fail.

**Not proven in Fusion.** I tried the same in Fusion with the real RS04s, and it passed with the rod's angle flipped too, so that test proved nothing, and I removed it. Joints set from the API moved occurrences' boxes after `computeAll`, but neither `analyzeInterference` nor saved pictures followed. So every Fusion picture and clash here is at the zero pose.

## How long it takes

| | Big duck, stand-ins | Big duck, real actuators |
|---|---|---|
| Moving parts in the assembly | 16 | 24 |
| Links built and saved | 281-351 s | **about 430 s, 95 s of it reading the RS04 once** |
| The assembly's refresh, 23 joints, clash check, pictures | 53 s | 130-147 s |
| Crop pictures, 72 | | 30 s |

## Joints

All 23 took 98 % of both limits with none refused. That's Fusion's joint limits, read back as numbers: nothing checks what hits what on the way.

## Clashes

266, at the zero pose, down from 353 on the first build with real shapes. `reports/fusion_interference_big.json`, boxes in `reports/fusion_clash_boxes_big.json`. Each was read by type and link, and those on the left and middle links by box.

**Against the real actuators: 0.** No plate, flange, screw or pin clashes with a real case or rotor. Screws are drawn at their core diameter, so they'd clash if they missed a tap hole, ran too long or met a cap screw. The first build found 8 real ones that way:

- RobStride's RS03 cap screws in the bridge and cradle, and 4 mount screws run into them. Those are the 4 rear sites that aren't free.
- A thigh cover's post into the knee's rear step, at 43 mm from its axis.
- Hip yaw housing screws into a body post and computer standoffs.
- The hip pitch's full screw head, 0.2 mm into the thigh plate.

### Across a joint, where a clash is a real flaw: 2

| Clash | What it is | Done |
|---|---|---|
| Chain into 25T sprocket, 0.58 cm3 each strand | a chain drawn as 2 straight bars tangent to the pitch circle | a drawing, not a flaw. Chain and tensioner aren't designed |

The 4 knee-rod clashes are gone.

### Inside one link: 264

Within a link everything is one rigid lump, and these are where parts are drawn into each other.

| Types | Count | Largest | Meaning |
|---|---|---|---|
| metal and metal | 148 | head rail in beak lug, 9.4 cm3; foot plate and ear, 8.8 cm3 | mostly the checks' 0.5 mm overlap, a joint read as joined. **Those are the frame joints with no fasteners.** A few are parts run into each other, like the ear into the foot plate |
| panel and metal | 37 | foot plate in the sole, 13.6 cm3 | panels have no pockets for what they meet |
| metal and steel | 23 | neck boss in spine, 2.4 cm3 | the same 0.5 mm, and press-fit bores 0.05 mm under size |
| panel and panel | 21 | eye ring in eye lens, 113 cm3; thigh cover pieces, 33 cm3 | the eye is solid discs; cover pieces overlap, instead of meeting at a seam |
| bearing and metal or steel or bearing | 24 | ankle ear in its bearing housing, 1.3 cm3 | seats 0.1-0.2 mm under size, and the foot's housing has no proper seat |
| box and metal or box | 7 | battery in deck, 11 cm3 | the box overlaps the plate, so they read as joined |
| steel and steel | 3 | 13T sprocket in chain | a chain drawn tangent |
| head frame and bill panel | 1 | 5.8 cm3 | panel not relieved |

## What's still not buildable

- **Frame joints have no fasteners:** cheeks to beam, ties, ribs, bridges, posts, standoff rings, covers and panels, and the yaw retainers' screws. They hold the robot up. No assembly order exists, so none is checked.
- **Rods aren't retained.** The pin ends 0.3 mm from the thigh plate, so there's no room for a circlip. The lane needs to widen, or the rod's bush needs a shoulder. A 5 mm rod with a 4 mm wall around its bush takes 2-4 kN, unchecked.
- **Solid parts with assumed fill:** the yoke, spine and beam. Their pockets may take what they need.
- **The 13T sprocket** has a plain face for 9 M5 and 3 pins. A bought one doesn't. The chain and tensioner aren't designed.
- **The beak's drive** isn't designed. The head's boxes are placeholders.
- **Cables** have a way out of each plate. Their routes and loops aren't drawn, and nobody knows they reach.

## What the pictures show

Looked at: `docs/images/fusion/big/crops/`, 72 close crops, 12 joints from 6 sides each, on the left and in the middle, skin hidden, at the zero pose, as 12 contact sheets, 500 px a view. Whole robot from three-quarter. The rods only with the outer rear plate hidden, at the zero pose, where they run from crank pin to lever pin as drawn.

- **Hips and knee stators:** real cases on real plates, each with its window and cable sleeve. Hull plates show as 24-sided polygons, a drawing limit.
- **Hip yaw:** a plain drum from outside. Bearing and flange can't be seen in it, and I didn't cut a section to look.
- **Hip roll:** the hollow yoke's screws are visible through it.
- **Neck:** bosses and heads through the window. The spine is still a plain bar.
- **Head yaw and roll:** lobed RS03s with RobStride's cap screws through their holes. Plugs clear of the plates.
- **Ankle:** real case, ring and two plates, 6 ear screws. The shin stops 2 mm over the case.
- **Beak:** the RS00 lies on its mount by a line. A placeholder.

Not looked at: the right leg (the left's mirror in the spec, and the same actuators turned), any other pose in Fusion, `links/` pictures one by one, and `back`, `side`, `under` and `top` of this build.

## Not done

- A one-document build, `.f3d`, `.step`, videos. An export would hold RobStride's models: that's the user's call, and it waits on their licence.
- Measuring a real actuator, the thing the thread question needs.
- The old `big assembly` document, with stand-in actuators' joints, is still in the hub, stale. This build's is `big assembly real`. Deleting one is for the user.
