# Training milli to walk

Uses [microduck_rl](https://github.com/pollen-robotics/microduck_rl), Pollen's trainer (mjlab, MuJoCo Warp, PPO). Its code is Apache-2.0 and its meshes are CC BY-NC-SA, so
this repo doesn't include a copy: [trainer/milli_trainer.patch](../trainer/milli_trainer.patch) adds milli to it, and milli's model is generated from this repo's spec.

## Where it stands

**Not walking straight yet.** Results from the checkpoint at iteration 2000 of 3000, told to walk straight ahead at 0.3 m/s for 8 s, 128 robots, randomization on and pushes off:

| Measure | Result |
|---|---|
| Stayed up | 100 % |
| Start-to-end speed, median | 0.24 m/s |
| Turning, median robot | 0.29 rad/s (about 17 deg/s) |
| Turning, 90th percentile | 0.68 rad/s |

This is simulation only, and nothing has run on a real robot. An earlier check, at iteration 750, had the hip yaw servos at stall a third of the time.

## Train the all-Dynamixel duck

No policy for its current design exists yet. Its older walks were trained with foot switches, on a model that has since changed. After the set-up below, on a machine with a big GPU, this trains the walk, the get-up and the head roll in turn, tests each and exports it to `pi/models/` for [the Pi code](../pi/README.md):

```bash
bash ../duck-droids/trainer/train_dynamixel.sh
```

The script hasn't been run yet. The head roll may well not come out: no policy has done it so far.

### A walk without the IMU, at the real gains, with the joints' slop

`milli_slop_env_cfg.py` in the trainer trains the all-Dynamixel duck's walk in two stages, so it can later run without the IMU. Started 2026-11-22. A first run at microduck's 0.96 N m was stopped at iteration 846; a second at the datasheet's limits, from scratch, stalled at 1 s episodes (its policies fell before learning anything, on the weakest servo draws with pushes on). The third, running, starts from the first's iteration 750 (action noise reset to 0.5) and a curriculum: it starts every servo at 0.52 N m and kp x0.9-1.0 with no pushes, and widens to the full ranges and pushes in six stages, each when episodes average 600 steps (12 s). Nothing has finished training yet.

It gives two policies, each exported to `pi/models/` as an ONNX with a JSON beside it that lists its input blocks in order (size, history, units, delays), the joint order, the standing pose and the servo numbers it was trained with:

- `walk_imu`: the teacher's actor, IMU + joints + last action. For the duck with its Pi Zero and IMU on board.
- `walk_blind`: the DAgger student, joints + last action, each with 0.2 s of history, and the commands. Every input comes from servo bus reads or the policy itself, so a PC driving the servos over USB can run it with no IMU.

```bash
bash ../duck-droids/trainer/train_slop.sh teacher-warm     # stage 1 from the 0.96 run's model_750 (or: teacher, from scratch), 3000 iterations, ~2.5 h on an RTX 5090
bash ../duck-droids/trainer/train_slop.sh after-teacher    # then: export walk_imu, train and export walk_blind, evaluate both, the baseline
```

The evaluation runs both policies with pushes on and the same seed (`eval_slop_imu.txt`, `eval_slop_blind.txt` in the trainer's folder). The baseline is the student's inputs trained by PPO alone, with no teacher. The servo numbers can be changed without editing code, before the trainer loads the task: `MILLI_PEAK_NM` lowers the top of the torque range (never above 0.52), one number or `leg=..,neck=..,head=..`, and `MILLI_KP` sets the top of the stiffness range likewise, in N m/rad.

What its robot has that the other tasks' doesn't:

| | What | Measured? |
|---|---|---|
| Gains | Position P as `pi/stand_test.py` stood the duck: legs 800, neck 1200, head 600, so kp 2.2, 3.3, 1.65 N m/rad at most (the other tasks use 0.55, P 200, everywhere). Each joint's kp is drawn per episode between 1/2.2 of that and it: legs 1.0-2.2. The model is `robot/milli_dynamixel_realgain`, from `tools/make_rl_model.py` (`DEPLOYED_P`) | The P values are; kp per P is microduck's identification; the stand test suggests ~1.3 at the knee. D gains not modelled |
| Torque | ROBOTIS's XL330-M288 datasheet at 5 V as a hard ceiling: 0.52 N m stall, 10.8 rad/s no-load (`spec/actuators.json`, which `tools/make_rl_model.py` now uses for the XL330 in place of the recipe's 7.4 V figures, 0.96 N m and 16 rad/s). Each servo's ceiling is drawn per episode in 0.30-0.52 N m, a penalty grows near it, and another for RMS torque over ~2 s above the rated 0.17 N m. The user's call: the walk may underperform, the motors mustn't burn | 0.30 (the 800 mA cap, a sagging supply) is unmeasured; rated is an estimate, a third of stall |
| Backlash | ±1° about every servo axis, microduck-style; the encoder, and the servo's own position loop, read through it | No: microduck's figure |
| Sag | A passive hinge across each hip pitch and knee servo, after it (`passive_<joint>_sag`), about the forward axis. Per episode: travel 0-3°, spring 2-60 N m/rad, damping 0.002-0.03 N m s/rad. The hip yaw and roll have the hinge too but locked (0.01°): with their bearings in, they no longer sag (the user, 2026-11-22) | No: all guesses, until the sag is measured |
| Physics step | 2 ms (the other tasks 5 ms), still 50 Hz control | Needed for the ±1° stops to hold: at 5 ms they reached 2-3° |

The slop is added to the loaded model in the trainer, so `pi/sim` keeps the nominal duck (its servos now follow each servo's `POSITION_P` register). Nothing observes the passive joints but the critic.

Stage 1, the teacher, has the usual inputs: IMU, joint positions and speeds, its previous action, the commands. Stage 2, the student, sees only the joint positions and speeds and its previous action, each with 10 steps (0.2 s) of history, and the commands: no gyro, no gravity. It learns by DAgger (`DaggerFromTeacher` in the trainer's `distill.py`): it acts, the frozen teacher labels each state it visits from its own inputs, and it regresses onto those labels; for the first 100 iterations the teacher acts some of the time. An auxiliary head predicts the body's tilt and speed from the student's inputs, after Blind Dexterity (Bhatt et al., arXiv 2608.29487), who got 90 % survival under pushes without the IMU against 96 % with it.

**Before running a policy trained here on the duck:** the Pi code writes position P 200 to every servo (`pi/config/dynamixel.json`), and these policies expect 800 / 1200 / 600. `pi/stand_test.py` caps the leg current at 800 mA, about half of stall: the low end of the torque range stands in for it. `pi/config/dynamixel.json` still says 0.96 N m and 16 rad/s; `pi/sim` now takes each joint's numbers from `pi/sim/model/home.json` instead.

`scripts/milli_eval.py` now keeps the training's pushes on; `--no-push` gives the old behaviour, which the table above used. For these tasks pass `--task` and `--model milli_dynamixel_realgain`.

### microduck's other skills

`milli_skills_env_cfg.py` in the trainer ports four more of Pollen's microduck tasks, for the hybrid and the all-Dynamixel duck. Name them to train them: `bash ../duck-droids/trainer/train_dynamixel.sh sitstand groundpick kickright kickleft`.

| Task | What it does | What changed for milli |
|---|---|---|
| `Mjlab-SitStand-Flat-Milli-Dynamixel` | Sits down and stands up on command, gently, head steerable in both | milli's sitting pose (its knee stops at 1.1 rad, microduck's at 1.35). Every height maps between milli's measured sitting (0.134 m) and standing (0.170 m) heights |
| `Mjlab-GroundPick-Flat-Milli-Dynamixel` | Lowers the beak to just above the floor and comes back up, in 4 s | a `mouth_tip` site at the beak's front, from `tools/make_rl_model.py` |
| `Mjlab-BallKick{Right,Left}-Flat-Milli-Dynamixel` | Kicks a 70 mm ball forward with one foot, then stands | the ball 84 mm ahead and 45 mm out: microduck's clearance past milli's toe |

Each builds and steps without errors or NaNs (64 robots, 3 s of small random actions, 2026-11-22). None has trained, and there's no eval script for them yet. Not ported: VelStand, which starts from microduck's own trained policies, so it waits for milli's walk; spin and the roller tasks, which are for microduck on wheels.

## Set it up

You need an NVIDIA GPU (the scripts ask for `cuda:0`), Python 3.12 and [uv](https://docs.astral.sh/uv/). The steps below were tested on Windows with an RTX 5090, apart from the fresh `uv sync`, which an earlier setup ran.

1. Clone the trainer next to this repo, at the commit the patch was made against, and apply the patch:

```bash
git clone https://github.com/pollen-robotics/microduck_rl ../microduck_rl
```

```bash
git -C ../microduck_rl checkout bae39f5
```

```bash
git -C ../microduck_rl apply --ignore-whitespace "$PWD/trainer/milli_trainer.patch"
```

2. Make the trainer's environment, and activate it. Use the activated environment's commands from here on, as `uv run` can put the CPU-only PyTorch back:

```bash
cd ../microduck_rl
```

```bash
uv sync
```

```bash
source .venv/bin/activate
```

On Windows, use `.venv\Scripts\activate`. `uv sync` installs a CPU-only PyTorch there, so replace it:

```bash
uv pip install "torch==2.9.1" --reinstall-package torch --index-url https://download.pytorch.org/whl/cu128
```

3. In another terminal, in this repo, generate milli's two models into the trainer. The trainer won't import without both. This needs a Python with numpy, scipy, trimesh, manifold3d, mujoco, Pillow, imageio and imageio-ffmpeg. Rerun it after any design change:

```bash
python tools/make_rl_model.py ../microduck_rl/src/mjlab_microduck/robot/milli
```

```bash
python tools/make_rl_model.py ../microduck_rl/src/mjlab_microduck/robot/milli_salvage --salvage
```

The floor skills and the other three [servo recipes](DETAILS.md#four-servo-recipes) need their own models too, and the trainer won't import without them. In bash:

```bash
R=../microduck_rl/src/mjlab_microduck/robot; python tools/make_rl_model.py $R/milli_contact --contact; for r in dynamixel feetech hd1910; do MILLI_RECIPE=$r python tools/make_rl_model.py $R/milli_$r; MILLI_RECIPE=$r python tools/make_rl_model.py $R/milli_${r}_contact --contact; done
```

## Check before a long run

In the trainer. This resets 256 robots and holds still with zero actions: soles on the floor, and few or none falling in 2 s.

```bash
PYTHONUTF8=1 python scripts/milli_sanity.py
```

## Train

Smoke test first, which only proves the code runs. Then the full run: 4096 robots, 3000 iterations, about 75 minutes alone on an RTX 5090. `WANDB_MODE=offline` keeps the logs local.

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli --env.scene.num-envs 64 --agent.max_iterations 5
```

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli --env.scene.num-envs 4096
```

Checkpoints go to `logs/rsl_rl/milli/`, every 250 iterations.

`Mjlab-Velocity-Flat-Milli-Salvage` trains the same recipe on the servos of a dismantled SO-101 pair: C046 at the hip yaws, C044 at the knees, C001 at hip roll, hip pitch and ankle. Its checkpoints go to `logs/rsl_rl/milli_salvage/`. That run hasn't been tested for walking yet.

Each recipe has three tasks, none with a finished, tested result yet. Hybrid: `Mjlab-Velocity-Flat-Milli`, `Mjlab-StandUp-Flat-Milli`, `Mjlab-Roulade-Flat-Milli`. For the others, add `-Dynamixel`, `-Feetech` or `-Hd1910` to the name. Test them with `--recipe dynamixel`, `feetech` or `hd1910` on `scripts/milli_eval.py` and `scripts/milli_skill_eval.py standup|roulade`. With zero actions, the all-Dynamixel and HD-1910 robots and half of the all-Feetech robots fall within 2 s in the check above, as do most of microduck's own, so that check's "few or none falling" applies to the hybrid only. Run at most three trainings at once on one GPU: four, beside a heavy CPU job, reset the display driver and killed every run.

## Test a checkpoint

Don't judge from the training reward. In the trainer, this runs fixed commands and reports survival, speed, each servo's load and speed, and each robot's real path and turning. It uses the latest checkpoint unless you name one. Add `--salvage` for the salvage task:

```bash
PYTHONUTF8=1 python scripts/milli_eval.py --envs 512
```

The per-robot numbers matter: mean speed in the body's frame counts walking in a circle as speed, and left and right turners cancel in an average.

## See the walk

Record a walk in the trainer, then render it from this repo in milli's colours, in MuJoCo's classic blue scene:

```bash
PYTHONUTF8=1 python scripts/milli_eval.py --envs 64 --only "forward 0.3" --seconds 12 --traj walk.npz
```

```bash
python tools/render_walk.py ../microduck_rl/walk.npz walk.mp4
```

## What's different from microduck's recipe

Run `scripts/milli_audit.py` in the trainer to print every setting the task has loaded. The reasons are at the top of `tasks/milli_velocity_env_cfg.py`.

**Changed for milli:**

- **The robot:** `tools/make_rl_model.py` gives milli microduck's names, joint directions and order, so the recipe's rewards and observations apply. The beak is locked.
- **Standing pose:** level, with the feet 42 mm forward, until the centre of mass is over the soles.
- **Foot switches:** two booleans added to the policy's inputs, from sole contact, except on the all-Dynamixel duck, which has none: joints and IMU only, as microduck.
- **Servos:** a DC motor model per servo type, with each type's own gain, stall torque and no-load speed. microduck's measured BAM model fits only the XL330.
- **Reset height:** the recipe's 12-13 cm was microduck's; it dropped milli from 12 cm at every reset. Now 0-2 mm.
- **Servo randomization:** friction, damping and armature each +-30 %, as they're scaled or copied. The recipe's friction setting did nothing here.
- **Mass randomization:** all links, about +-20 %, as milli's masses are estimates (the recipe: trunk only, about +-5 %).
- **Head commands:** within milli's limits (neck 0.12 rad back, 0.8 forward; head pitch +-0.8), as the recipe's +-1.1 passed them.
- **Scaled by size** (height x 1.22, time x 1.10): foot lift, air time, pushes, centre-of-mass offsets.

**Kept from microduck, on purpose:**

- **Speed commands** (+-0.4 m/s): milli's longer leg against its slower servos.
- **Foot friction** 0.7-1.3: both soles are TPU, and neither is measured.
- **IMU and encoder noise:** similar parts, unmeasured.
- **Servo delay** 15-30 ms: microduck's, an estimate of a serial bus at 50 Hz.
- **Reward weights and curriculum timing:** dimensionless, or time in training.

**Lost with the BAM model, not replaced:** load-dependent friction, battery voltage and its sag under load. milli's servo torque is modelled at a fixed voltage.

## A robot far bigger than its recipe

Its set-up, training and evaluation, step by step: [big/REPRODUCE.md](big/REPRODUCE.md#5-train-the-walk).

The big duck (`Mjlab-Velocity-Flat-Milli-Big`) showed what scaling this recipe does and doesn't do. `scale_for_big` in the velocity task handles any robot over 3 times microduck's height:

- **Units.** Speeds by the square root of size. The angular momentum penalty by (mass x height^1.5)^2: at 113 kg it was millions of times too strong. Foot slip, clearance and swing penalties by height. Self-collision's force threshold by mass.
- **Scaled correctly, it stood still.** 0.001 m/s told 0.4, staying up 100 % of the time. Its air-time reward needed a foot up for 0.33 s, which never happens by chance at this weight, and standing already earned most of the tracking reward. Shorter air time and tighter tracking weren't enough.
- **So a stepping clock:** a phase input, and rewards for each foot's contact and lift against it. A 1.2 s stride is an estimate. It stepped within 500 iterations. This makes its walk not like-for-like against the small ducks.
- **Stop penalties on every joint.** Its knee sat on its stop 83-92 % of the time, pressing past it, on the recipe's weak penalty. Torque didn't fall with mass: that was the clue.
- **A sustained load penalty,** `over_rated`: RMS torque over about 2 s above the rated torque. Near-stall penalties start at 70 % of peak, and at 3:1 peak to rated a joint can sit at twice its rating and pay nothing.

Check a new size early, against a robot that learned, at iterations 250-750: each reward term (one at zero has no path to it), real speed, and time at each joint's limits (`scripts/milli_limits.py CHECKPOINT TASK`). Survival alone says nothing. `tools/leg_limits.py` compares foot lift, lean and static torque between two models.

Its gains (kp 100-400, kd = kp / 40) are a first guess, and the crank's changing ratio is modelled as one number: its weakest torque and, near the bent end, its speed.

## What's assumed, and not measured

| What | Value | Source |
|---|---|---|
| STS3215-C044 / C046 stiffness | 9.9 / 7.6 N m/rad | Open Duck's 17.8 for the C001, scaled by gear ratio |
| XL330 stiffness | 0.55 N m/rad | microduck's identification |
| XC330 stiffness | 0.98 N m/rad | the XL330's, scaled by stall torque |
| STS3215 peak torque | C044 2.69, C046 1.41 N m, at 7.4 V | retailer listings; no Feetech page found; one retailer gives the C044 1.57. Sources in `spec/actuators.json` |
| Servo delay | 15-30 ms | microduck's, kept as an estimate |
| Voltage sag, load-dependent friction | none | in microduck's BAM model; not ported |
| Reward weights, command speeds | microduck's | see above |
| Masses, friction | see the spec | infill, wires and friction are estimates |

So a policy trained here shows whether the design can walk in simulation. It isn't ready for a real robot: that needs a measured servo model, and delay and backlash in the sim.
