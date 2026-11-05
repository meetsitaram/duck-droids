# Big duck in Fusion

**NOT SAFE TO BUILD.** A model that builds in Fusion says nothing about strength. Clash checks test whether shapes overlap, not whether a frame holds: see [Open before ordering](BOM.md#open-before-ordering).

![The big duck in Fusion, from the front](../images/fusion/big/34.png)

## How long it takes

The worry was its size. It turned out not to matter: Fusion's time goes with features, not metres, and the big duck has fewer features than a small one.

| | All Dynamixel | Big duck |
|---|---|---|
| Links | 16 | 16 |
| Bodies | 514 | about 500, with rods, chain and covers |
| Printed parts joined and rounded | 43 | 0 |
| Holes and pockets cut | 404 and 117 | 0 |
| Lofts, and the plane cuts on them | 10 and 3 | 54 and 206 |
| Links built and saved | about 9 min, assembly included | **281 s** |

By link, in seconds: head 176, trunk 36, beak 12.5, and each of the other 13 under 6. The head is the cost: 30 hood panels, each a loft cut by up to 5 planes.

So it is not a fair comparison. It's quick partly because the frames have no holes, pockets or fixings. Those are what's missing, and adding them will cost what they cost the small ducks.

## The hang

The first full build held Fusion far too long. Links, clashes and pictures were written by about 00:42, 6 minutes in. The call then didn't return, and the client gave up at its 40-minute limit. The lease ran out at 01:01, after hd1910 had waited 22 minutes. A lease that ends doesn't stop the call behind it, so the next agent's turn was no use either.

At 01:21 Fusion still showed "big assembly", not responding, and using some CPU. Its top-level windows showed no dialog, but the window couldn't be captured, so a dialog isn't ruled out. The cause isn't known. The step after the pictures is saving the assembly, so that's the first place to look. So `pipeline.sh` now stops the big duck before its assembly, unless told `BIG_ASSEMBLY=True`, and the assembly isn't to be run again without asking.

Whether the assembly saved, and in which hub project, isn't known either: the window's title read "big assembly (tinkerbuggy)", though the script looks for my-projects / duck-droids / big. To check once Fusion is back.

## Clashes

379, from the first full build, in `reports/fusion_interference_big.json`. They were all read by type and link: 357 are inside one link, and 22 cross a joint.

### Across a joint, where a clash is a real flaw

| Clash | Mirrored | What it is | Done |
|---|---|---|---|
| Inner thigh cover, hip piece, into rear hip roll actuator (8.4 cm3), yoke (2.0), cheek (1.9), its seat and 2 screws | yes | **a real flaw.** Covers are `decal`, so the offline checks never test them | piece and its post removed from the spec; not yet rebuilt |
| Inner thigh cover, knee piece, into hip roll cheek (0.16 cm3) | yes | **a real flaw,** small | **not fixed** |
| Body panel M into hip yaw drum (0.41 cm3) | yes | **a real flaw:** the drum reaches 8 mm into the panel's lower edge | clearance cut in the spec; not yet rebuilt |
| Knee rod into lever pin (0.39 cm3) | yes | the rod has no hole drawn. It's drawn at knee angle 0 and belongs to the thigh, as one body can't swing within a link | **not fixed:** rods need their own moving links, and bushes |
| Chain into 25T sprocket (0.58 cm3 each strand) | no | a chain drawn as 2 straight bars tangent to the pitch circle | a drawing, not a flaw. Chain and tensioner not designed |

Mirrored ones count twice in the 22.

**None of the sweep is tested for covers or rods.** This check is at the zero pose only, and the covers and rods are left out of the offline sweeps. **Whether Fusion accepted every joint's limits isn't known:** the script's printed results, the refused joints among them, were lost when the call timed out. Only the files it wrote survive: the clash list, the link times and the pictures.

### Inside one link, which are not assemblies

Within a link everything is one rigid lump in the model, and these overlaps say that **no joint between those two parts has been designed.** None of them can be built as drawn, and none has been fixed.

| Types | Count | Largest | Meaning |
|---|---|---|---|
| metal and metal | 139 | neck output in the solid neck spine, 30 cm3 | plates running into blocks, with no fastening or pocket |
| panel and metal | 52 | foot plate in the sole, 13.6 cm3 | panels have no pockets for what they meet, such as the foot plate |
| panel and panel | 17 | eye ring in eye lens, 113 cm3; thigh cover pieces, 33 cm3 | the eye is solid discs; thigh cover pieces overlap, instead of meeting at a seam |
| metal and screw | 38 | 0.08 cm3 each | no screw holes are cut |
| seat and metal or actuator | 58 | 4.8 cm3 | the thin rings the spec adds so the checks read touching parts as one |
| steel and metal | 24 | head pitch shaft in its yoke, 10 cm3 | shafts through plates with no bores |
| bearing and metal | 10 | hip yaw outer race in its drum, 1.9 cm3 | no seats cut |
| bearing seat and shaft | 8 | 0.08 cm3 | races drawn a hair inside the bore |
| battery or board and metal, or screw | 7 | battery in deck, 13 cm3 | the box overlaps the plate by 0.5 mm, so they read as joined. Deck screws run up into the computer box |
| steel and steel | 3 | shaft in sprocket, 10 cm3 | no bore; a chain drawn tangent |
| actuator and metal | 1 | beak actuator in its mount, 0.18 cm3 | a placeholder: the beak's drive isn't designed |

## What the pictures show

Looked at from the front three-quarter, side, back and below, at full size.

- It reads as the duck: hood, eye, orange band and jaw, a long neck, the body, and the hip frames under it.
- **The inner and outer thigh covers look like loose flat plates,** standing off the thigh on thin posts. They were designed as flat shapes and it shows. Nothing joins them, and from below they look stuck on.
- **The head hangs 0.6 m in front of the neck,** and the side view shows how far that is from the feet. Nothing about it is checked for strength or for a fall.
- **The hip frame sits below the body, with a clear gap** and its two drums showing. The body panels don't reach the frame.
- **Above the jaw, from the side,** the frames show through a gap in the orange band.
- **From behind,** the hood has a square opening onto the head's frame plates, which the small duck's doesn't, and the jaw's frame shows under it.
- The real RS04 shape isn't here: these are plain cylinders.

Not looked at: close crops of each joint, and the views at other poses.

## Not done

- A rebuild with the fixes above, so these pictures and clashes are from before them.
- A one-document build for `cad/duck-droids-big.f3d` and `.step`.
- Videos: not until those exist, and not at the risk of holding Fusion from the others.
