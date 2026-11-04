# Assembly videos: the rules

Read before rendering any build or reveal video. Each rule below is a correction from the user. Follow them without being asked again, and add new corrections here as they come.

## Commands

```bash
python -I tools/fusion_call.py cad/fusion/reveal_frames.py --write    # one batch: set FIRST and LAST. 150 frames at a time, on the open model
python -I tools/reveal_video.py                                       # joins the frames, with the opening and the titles
python tools/render_pov_video.py                                      # the build video, about 20 minutes
```

Compress for sending: a phone viewer has a 30 MB limit, and the build compresses to about 11 MB with no visible loss.

## Two videos, two jobs

| | Reveal | Build |
|---|---|---|
| Length | about 30 s | about 5 min |
| Shows | what the robot is made of, not how to build it: motors, then skeleton, then electronics, then covers, on a slow turn | every step, in the build order |
| Made from | the real Fusion model (`cad/fusion/reveal_frames.py`, in batches, then `tools/reveal_video.py`) | the checked build order (`tools/render_pov_video.py`, from `tools/assembly.py`) |
| Text | one centred title per stage | the labels below |

A 30-second cut of the build is not a useful overview: it was unwatchable. Make the reveal instead.

## Framing

- **Portrait, always:** every assembly video, including clips for the guide. Reveal 1080 x 1920, build 720 x 1280.
- **The camera stays close, on the part that's moving,** and the whole part stays in frame.
- **See the work from the side it's happening on,** including from underneath: each part and screw group picks its view by counting its visible pixels (`best_view`), and the run lists the least visible. A fixed view from above hid the body's underside and the far side of the legs.
- **Test a finished robot's legs from the front and low,** under the covers. From above and the side, the covers hid them.
- **Open a reveal on the whole robot:** one second from the front with its title, then fade into the start. The first frame is the thumbnail.
- **End on the front, and hold:** the last seconds show the face and eye, on every video. Set where a turn ends first and work back from it; never let it land wherever it lands.

## What's on screen

- **Parts only:** no hands and no driver. Screws turn in by themselves.
- **Plain background:** one seamless pale colour for floor and sky, as in the reveal: no checker, no pattern, no horizon. A checkered bench looked bad in every version, and dark parts on a dark bench didn't read.
- **Nothing black behind the text:** set the sky as well as the floor, as a raised camera sees past the floor's edge.
- **Finished work goes out of frame:** parked parts must not sit under the labels.
- **No empty frames:** a section's first part is in view as soon as its label appears.
- **Portrait is narrow:** set the camera distance from the frame's width, so a whole robot being tested keeps its head in frame.
- **Contrast against every neighbour, not just the bench:** keep white parts below full brightness so they keep their shape, and use mid-grey screws, which show on both white covers and dark frames. Bright steel disappeared on white.
- **Keep the white parts shaded:** on a pale background they need light below full brightness to keep their edges.
- **Real colours:** the same servos, boards and steel screws as the model.

## Labels

The labels are there so the builder knows which parts they are using.

- **Name every part as it comes in, and say what it is:** the servo model, the bearing's number, or what it's printed in. For example "Left hip pitch servo: XL330-M288", "Left knee lid: printed, PLA".
- **Name the screws too:** the count, size and driver. For example "4 x M2 x 8 mm Phillips".
- **Two short lines, as in the reveal: centred dark text on the pale background.** The large line is the part or screws, the grey line is what it is, and they fade in when they change. Between parts, show the section's name.
- **No sentences on screen:** instructions and step numbers go in the written guide. More text than this was clutter.
- **No dark bands or coloured rectangles:** their sharp edges looked bad. A joint test is the large line, in green.
- **Top of the frame until the head starts, then the bottom,** so it doesn't cover the head. A thin pale edge keeps the text readable where a part passes behind it. At the bottom, keep it above the phone's own controls (90 px on a 1280 px frame).
- **No floating labels or leader lines on moving parts.**
- **A label appears with its part and clears when its step ends,** so it never names something that has left the frame.
- **A part with no type is a failure:** `part_kind()` must return one for every part. List them before rendering.

## Pacing

- **Group similar screws:** all the screws of one step and direction go in together.
- **Build the mirror side fast:** the first side is the lesson.
- **Test joints as a builder would:** move each joint when it can first move, with a "Test:" label, then every joint at the end.
- **Set the length with dry runs:** `fit()` finds the pace that lands on the target.

## Honesty

- **Parts move only along paths the assembly check has passed.** Never move a part into place by a way that was not checked.
- **Close by saying what's unproven:** nothing has been printed, so the video shows a checked plan, not a build.

## Before sending

1. **Test the labels first:** check all part labels and a mock frame in both label positions before a full render, and restart a render that began before the last edit. Let a test frame finish its fade-in, or the label looks faint. Say when a sheet of portrait frames is a sheet, or it looks like a landscape video.
2. **Read the least-visible list,** then check frames from every section, at their true shape (resizing a portrait frame to landscape hid problems): do the labels cover the work, is the part in frame, can you read the text at phone size?
3. **Don't rebuild Fusion for a video:** use the open model. Rebuild only if the robot changed.
4. **Send the MP4 itself,** as the user may be on remote control, where GIFs don't play and HTML doesn't open. A page is extra and has a 16 MB limit.
5. **Clips for the guide come from the approved build video,** not a separate render: MP4 on the page, short GIFs for GitHub.
