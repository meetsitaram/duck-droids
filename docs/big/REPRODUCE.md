# The big duck, from this repo

**Not safe to build.** This is how to regenerate everything the repo shows for the big duck: its checks, its Fusion model, its two videos, and a trained walk in simulation. See [OPEN_QUESTIONS.md](../OPEN_QUESTIONS.md) for what's undecided and [PAIRED_ACTUATORS.md](PAIRED_ACTUATORS.md) for the paired actuators.

Everything below runs from this repo's root. Commands are bash (Git Bash on Windows).

## What isn't in the repo, and where to get it

Nothing in this repo was copied from these. Fetch them yourself, under their own terms:

| What | Where | Used for | Terms |
|---|---|---|---|
| RobStride's RS04, RS03, RS00, power board and CAN hub models | github.com/RobStride/Product_Information, fetched by `python -I tools/fetch_servo_cad.py` into `%TEMP%/figrefs/robstride` | the Fusion model only: the real actuators | no licence file: keep them local, and don't commit or publish exports that contain them |
| The trainer, microduck_rl | github.com/pollen-robotics/microduck_rl at commit bae39f5 | training | Apache-2.0 code. Its meshes are CC BY-NC-SA 4.0: not used for the big duck |
| Fusion | Autodesk | the Fusion model | Autodesk's terms |

The repo holds this project's own work: the spec (`spec/big_duck.py`), the checks, the build scripts, the trainer patch (`trainer/milli_trainer.patch`, changes to microduck_rl's Apache-2.0 code), and renders made from the spec's own shapes.

## 1. Set up

Python 3.12. The design tools:

```bash
python -m pip install -r requirements.txt
```

The pipeline looks for Python at `$PY`. Point it at yours:

```bash
export PY=$(command -v python)
```

## 2. Spec and checks

Free, offline, as often as you like. Writes `spec/robot_big.json`, `reports/big/`, `docs/big/BOM.md`, `ASSEMBLY.md` and `CABLES.md`:

```bash
MILLI_RECIPE=big bash tools/pipeline.sh gates
```

Every line should say `0 failing`. The assembly order alone: `MILLI_RECIPE=big python -I tools/big_assembly.py`.

## 3. The Fusion model

Needs Fusion with its MCP server on: Preferences > General > API > Fusion MCP Server, at `http://127.0.0.1:27182/mcp` (`tools/fusion_call.py`). Fetch RobStride's models first (above): without them the actuators can't be placed.

```bash
python -I tools/fetch_servo_cad.py
```

```bash
MILLI_RECIPE=big BIG_ASSEMBLY=True bash tools/pipeline.sh fusion
```

One Fusion document per link in your hub's `duck-droids` project, then an assembly of them, with its clash check and pictures in `docs/images/fusion/big/`. About 15 minutes a turn: run it again to build the links it didn't reach (`BIG_SECONDS` sets the turn). What it found, and how the actuators were measured: [FUSION.md](FUSION.md). Notes on driving Fusion by script, and what to do when it stops answering: `references/fusion-mcp.md` in the droid-from-spec skill (github.com/tinkerdroids/design-and-build-skills).

Fusion grows over a long session. Restart it between long runs, and don't run heavy renders beside it on a 16 GB machine.

## 4. The two videos

Both render offline in MuJoCo from the spec's shapes, with no Fusion and no third-party files. The actuators are the spec's measured outlines, not RobStride's models.

```bash
MILLI_RECIPE=big bash tools/pipeline.sh reveal
```

```bash
MILLI_RECIPE=big bash tools/pipeline.sh video
```

They write `docs/images/assembly/big/reveal_30s.mp4` (30 s, the parts appearing on a turn) and `build_5min.mp4` (the checked assembly order, part by part and screw by screw), and clips in `clips/`. For a quick look first, a contact sheet: `MILLI_RECIPE=big python tools/render_big_video.py build --test` (or `reveal --test`); `BIG_EVENTS=40` renders only the first 40 steps. Before rendering videos, read `references/assembly-videos.md` in the droid-from-spec skill.

## 5. Train the walk

Needs an NVIDIA GPU. The full set-up is in [TRAINING.md](../TRAINING.md#set-it-up): clone microduck_rl next to this repo at bae39f5, apply `trainer/milli_trainer.patch`, make its environment. Then:

1. **The big duck's models** for the trainer, and the `trainer.json` that registers its tasks. Run with this repo's Python:

```bash
python tools/big_trainer.py ../microduck_rl/src/mjlab_microduck/robot
```

It writes `milli_big` and `milli_big_contact` there (generated from the spec, not committed), and should print a mass of about 98.6 kg and a height of 6.8 times microduck's.

2. **Check the task loads**, in the trainer's environment:

```bash
cd ../microduck_rl
```

```bash
PYTHONUTF8=1 python -c "import mjlab_microduck.tasks; from mjlab.tasks.registry import load_env_cfg; load_env_cfg('Mjlab-Velocity-Flat-Milli-Big'); print('ok')"
```

3. **Hold still first:** resets 256 robots and holds with zero actions. Soles on the floor, few or none falling in 2 s:

```bash
PYTHONUTF8=1 python scripts/milli_sanity.py Mjlab-Velocity-Flat-Milli-Big
```

4. **Smoke test, then the run.** The smoke test only proves the code runs:

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli-Big --env.scene.num-envs 64 --agent.max_iterations 5
```

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli-Big --env.scene.num-envs 4096
```

Checkpoints go to `logs/rsl_rl/milli_big/` every 250 iterations. Only the walk is meant for this duck: its StandUp and Roulade tasks register, but its spec says it can't get up off the floor.

**What scaling did last time,** and the terms added for it (a stepping clock, stop penalties, a sustained-load penalty): [TRAINING.md, A robot far bigger than its recipe](../TRAINING.md#a-robot-far-bigger-than-its-recipe). Its gains are a first guess.

## 6. Evaluate

Check early, at iterations 250-750, not only at the end. Survival alone says nothing.

- **Time at each joint's limits,** and whether it presses past them:

```bash
PYTHONUTF8=1 python scripts/milli_limits.py logs/rsl_rl/milli_big/<run>/model_<n>.pt Mjlab-Velocity-Flat-Milli-Big
```

- **Walking tests:** speed held against speed asked, falls, turning, pushes. `--recipe big` picks its task:

```bash
PYTHONUTF8=1 python scripts/milli_eval.py logs/rsl_rl/milli_big/<run>/model_<n>.pt --recipe big
```

Add `--only "forward 0.3" --traj walk.npz` to record one walk, then render it from this repo with `MILLI_RECIPE=big python tools/render_walk.py walk.npz walk.mp4`; `--nudge "2,150,0,0.2"` pushes the trunk 150 N forward at 2 s for 0.2 s.

- **Each reward term** in the run's logs: one that stays at zero has no path to it.
- **Leg loads against a model that learned:** `tools/leg_limits.py` compares foot lift, lean and static torque.

A policy here shows whether the design can walk in simulation. It isn't ready for the real robot: that needs measured actuator models, delay and backlash in the simulation, and the paired-actuator control in [PAIRED_ACTUATORS.md](PAIRED_ACTUATORS.md).
