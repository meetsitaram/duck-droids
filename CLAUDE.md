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
  (the build order: 0 failing), `python -I tools/buildable.py` (walls, one piece, load: a beam estimate), `python tools/render_assembly.py`,
  `python -I tools/make_docs.py` (BOM.md, docs/ASSEMBLY.md), `python -I tools/export_prints.py` (prints/). Fit is not strength: say which was checked. Masses from materials (`python -I tools/mass_model.py`).
- **Also:** `python -I tools/printable.py` (the exported parts: orientation, supports, MATE, SKIN, HEADS) and `python -I tools/beak_linkage.py`, 0 failing. Then Fusion: `references/fusion-mcp.md`.
- **Branches:** `main` has STS3215 ankles. `fusion-model` adds the first Fusion build and what it found. `xc330-ankle` keeps the version with Dynamixel XC330 ankles. Robot changes go on a branch.
- **Not proven yet:** nothing has been printed. LOAD in `tools/buildable.py` is a beam estimate, not FEA. Walking is untested;
  the video's walk is kinematic.
- **Servos:** `spec/actuators.json`: STS3215 C044 (1:191) and C046 (1:147), XC330/XL330-M288; the lower-ratio STS3215
  numbers are scaled from the C001, not measured: confirm before ordering.
- **References (local, never in the repo):** microduck's MJCF in %TEMP%/figrefs/microduck_rl (code Apache-2.0, meshes
  CC BY-NC-SA 4.0: look and proportions only, no geometry copied); Pollen's photos in reports/compare/photos;
  Open Duck Mini v2 (Apache-2.0, STS3215 dynamics) and SO-ARM100 (Apache-2.0, the STS3215 mesh) in %TEMP%/figrefs.
- **Electronics:** `docs/WIRING.md`. Raspberry Pi Zero 2 W in the head, with a FE-URT-1 (Feetech bus) on its UART and a U2D2 (Dynamixel) on its USB; 2S LiPo 850 mAh, on an XT30;
  2 8 A UBECs and the IMU in the body; camera on the back of the face.
- **Fusion:** Preferences > General > API > Fusion MCP Server, registered in `.mcp.json`. The model comes from `cad/fusion/build.py` and `spec/parts.json`. Finished models are saved in the hub at `my-projects` / `duck-droids`, as `duck-droids <recipe>`, then closed: one document open at a time. Otherwise don't save the Fusion document or commit
  unless the user asks. The user's SO101 assemblies are in the tinkerbuggy project.
