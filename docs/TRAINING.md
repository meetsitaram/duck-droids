# Training milli to walk

Uses [microduck_rl](https://github.com/pollen-robotics/microduck_rl), Pollen's trainer (mjlab, MuJoCo Warp, PPO; Apache-2.0 code), in a local copy at
`C:\Users\PC\projects\milli-rl`, branch `milli`. Its meshes are CC BY-NC-SA, so that copy stays off this repo.

## Set it up

1. Clone microduck_rl next to this repo, and add `robot/milli_constants.py`, `tasks/milli_velocity_env_cfg.py` and the task's registration.
2. Make its environment with `uv sync` (Python 3.12). On Windows that installs a CPU-only PyTorch, so replace it:

```bash
uv pip install "torch==2.9.1" --reinstall-package torch --index-url https://download.pytorch.org/whl/cu128
```

3. Generate milli's model into the trainer, from whichever branch's design you want. Rerun this after any design change:

```bash
python tools/make_rl_model.py ../milli-rl/src/mjlab_microduck/robot/milli
```

## Check before a long run

`scripts/milli_sanity.py`, in the trainer: resets 256 robots and holds still with zero actions. Soles on the floor, none fall in 2 s. A smoke test only proves the code runs.

## Train

Smoke test first, then the run (RTX 5090, 4096 robots). `WANDB_MODE=offline` keeps the logs local.

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli --env.scene.num-envs 64 --agent.max_iterations 5
```

```bash
WANDB_MODE=offline PYTHONUTF8=1 train Mjlab-Velocity-Flat-Milli --env.scene.num-envs 4096
```

Checkpoints go to `logs/rsl_rl/milli/`, every 250 iterations.

## What's different from microduck's recipe

Run `scripts/milli_audit.py` in the trainer to print every setting the task has loaded. The reasons are at the top of `tasks/milli_velocity_env_cfg.py`.

**Changed for milli:**

- **The robot:** `tools/make_rl_model.py` gives milli microduck's names, joint directions and order, so the recipe's rewards and observations apply. The beak is locked.
- **Standing pose:** level, with the feet 42 mm forward, until the centre of mass is over the soles.
- **Foot switches:** two booleans added to the policy's inputs, from sole contact.
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
