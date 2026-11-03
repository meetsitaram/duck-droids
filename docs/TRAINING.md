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

- **The robot:** `tools/make_rl_model.py` gives milli microduck's names, joint directions and order, so the recipe's rewards and observations apply. The beak is locked.
- **Standing pose:** level, with the feet 42 mm forward, until the centre of mass is over the soles.
- **Foot switches:** two booleans added to the policy's inputs, from sole contact.
- **Servos:** plain position actuators with a torque limit. microduck's measured BAM model fits only the XL330.

## What's assumed, and not measured

| What | Value | Source |
|---|---|---|
| STS3215-C044 / C046 stiffness | 9.9 / 7.6 N m/rad | Open Duck's 17.8 for the C001, scaled by gear ratio |
| XL330 stiffness | 0.55 N m/rad | microduck's identification |
| XC330 stiffness | 0.98 N m/rad | the XL330's, scaled by stall torque |
| STS3215 peak torque | C044 1.06, C046 0.81 N m | scaled from the C001; a listing gives the C044 2.7 |
| Servo delay and voltage sag | none | microduck's recipe has both, in its BAM model; not ported yet |
| Rewards, command speeds | microduck's, unscaled | milli is 1.2 x taller and 2 x heavier |
| Masses, friction | see the spec | infill, wires and friction are estimates |

So a policy trained here shows whether the design can walk in simulation. It isn't ready for a real robot: that needs a measured servo model, and delay and backlash in the sim.
