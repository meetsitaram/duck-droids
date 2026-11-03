# milli (a microduck-sized biped on Feetech STS3215 legs): notes for Claude

milli has microduck's look (Pollen Robotics; spec/targets.json) on the SO-101 arm's servo, the Feetech STS3215, at
the hips, knees and ankles, and ROBOTIS XC330/XL330s at the neck and head. Forked from echo (github.com/meetsitaram/echo),
the Figure 03 replica: use the `humanoid-from-spec` skill (`.claude/skills/humanoid-from-spec/SKILL.md`) for the
method, step by step, and read `LESSONS.md` first (echo's lessons; milli's go in its own section).

- **Frame and units:** metres; X forward, Y left, Z up, floor z = 0; zero pose standing with straight legs, head
  level, beak shut. The renders and compare stand milli with its knees bent, as microduck's model stands.
- **Source of truth:** `spec/robot.py` (anchors in "proportions" set every height from the servo cases and their
  clearances) -> `python -I spec/robot.py` -> `spec/robot.json`. Never hand-edit robot.json or the Fusion document.
- **Every change:** `python -I spec/robot.py`, `python -I tools/checks.py` (0 failing), `python tools/compare.py`
  (microduck beside milli at one scale), look at the pictures. If a part or screw changed: `python -I tools/assembly.py`
  (the build order: 0 failing), `python tools/render_assembly.py`, `python -I tools/make_docs.py` (BOM.md, docs/ASSEMBLY.md). Masses from materials (`python -I tools/mass_model.py`).
- **Servos:** `spec/actuators.json`: STS3215 C044 (1:191) and C046 (1:147), XC330/XL330-M288; the lower-ratio STS3215
  numbers are scaled from the C001, not measured: confirm before ordering.
- **References (local, never in the repo):** microduck's MJCF in %TEMP%/figrefs/microduck_rl (code Apache-2.0, meshes
  CC BY-NC-SA 4.0: look and proportions only, no geometry copied); Pollen's photos in reports/compare/photos;
  Open Duck Mini v2 (Apache-2.0, STS3215 dynamics) and SO-ARM100 (Apache-2.0, the STS3215 mesh) in %TEMP%/figrefs.
- **Electronics:** Raspberry Pi Zero 2 W with a servo hat (both buses), 2S LiPo ~800 mAh (the smallest that runs
  it, user 2026-11-02), 5 V regulator, IMU, Pi camera in the head.
- **Fusion:** the user's SO101 assemblies are in the tinkerbuggy project. Don't save the Fusion document or commit
  unless the user asks.
