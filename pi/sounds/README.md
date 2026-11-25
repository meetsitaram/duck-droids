# The duck's sounds

`microduck/` holds microduck's 13 emotion sounds, unchanged, from Pollen Robotics:

- **Source:** github.com/pollen-robotics/microduck, folder `robotd/emotions/`, at commit
  `93b26bbf2acf73babb53cd6b47e800d2661f54f4` (fetched 2026-11-24). Pollen cut that set from
  github.com/pollen-robotics/microduck_emotions (its `sounds/` and `keyframes/`), where the sounds were made with
  its own voice synth, `quack.py`.
- **Licence:** Apache License 2.0, both repositories. A copy of microduck's licence is `microduck/LICENSE`. No
  NOTICE file came with them. The files are as published: nothing changed.
- **What's here:** for each emotion, `<name>.wav` (mono, 16-bit, 48 kHz, 0.7 to 6.6 s) and `<name>.json`, the head
  and body motion Pollen designed with it (keyframes in seconds, deltas from home in radians: neck, head pitch, yaw
  and roll, body pitch and height, beak `mouth` 0 to 1, already in time with the sound). milli doesn't play the
  motions yet; they're kept so that it can.

Emotions: angry, curious, defiant, devastated, excited, impatient, laugh, mmh, mock, no, sad, yes, yes_fast.

Play one: `python -m duck.sound yes` from `pi/` (`pi/duck/sound.py`). On the Pi it goes to the Bluetooth speaker
that `bt_speaker.sh` pairs (pi/README.md, "A Bluetooth speaker").

**Can the repo keep a copy?** Yes. Apache-2.0 allows copying and redistributing them, changed or not, provided the licence text
goes with them (`microduck/LICENSE`), the source is credited (this file), and any file we change says so. Both upstream repositories
say Apache-2.0 for the whole repository, these files included (checked 2026-11-24: GitHub's licence field for
`pollen-robotics/microduck` and `pollen-robotics/microduck_emotions`, and the latter's README, "Licence: Apache-2.0"). This differs
from microduck's robot meshes (CC BY-NC-SA, CLAUDE.md), which stay out of the repo. If you'd rather not ship them anyway, delete
`microduck/` and use the fetch below.

**Onto the robot:** `bash pi/deploy.sh USER@ADDRESS` copies all of `pi/` to `~/duck` on the Pi, `sounds/` included, so the duck has
them after any deploy. On the Pi, `python emote.py yes` plays a sound with its head, neck and beak motion (`pi/emote.py`), and
`python -m duck.sound yes` plays the sound alone.

One difference from Pollen's design repo: there, devastated's sound starts 0.3 s into its motion (`sound_at_s`); microduck's robot
copy, the one here, has no such field, so emote.py starts every sound with its motion.

To fetch them again (from the repo root, Git Bash, `gh` signed in or not):

```bash
SHA=93b26bbf2acf73babb53cd6b47e800d2661f54f4
for n in angry curious defiant devastated excited impatient laugh mmh mock no sad yes yes_fast; do
  for e in wav json; do curl -sfL -o pi/sounds/microduck/$n.$e \
    https://raw.githubusercontent.com/pollen-robotics/microduck/$SHA/robotd/emotions/$n.$e; done; done
```
