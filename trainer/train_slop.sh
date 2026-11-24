#!/bin/bash
# The all-Dynamixel duck's walk at its real servo gains, with gear backlash and single-horn sag (milli_slop_env_cfg.py in the trainer), in two
# stages, giving two policies: walk_imu (with the IMU) and walk_blind (servo bus reads only). Run from the trainer's folder, environment active.
#   bash ../duck-droids/trainer/train_slop.sh teacher          stage 1, 3000 iterations
#   bash ../duck-droids/trainer/train_slop.sh after-teacher    waits for it, then exports walk_imu, trains and exports walk_blind (DAgger),
#                                                              evaluates both with pushes on and the same seed, then the PPO-only baseline
#   other stages: student [CKPT] | baseline | export-imu CKPT | export-blind CKPT TEACHER | eval-pair TEACHER STUDENT
# Servo overrides, read when the trainer loads the task: MILLI_PEAK_NM=0.28 or "leg=..,neck=..,head=..", MILLI_KP likewise (N m/rad).
# The stages are in slop_stages.sh. ITERS and ENVS override the defaults.
exec bash "$(dirname "$0")/slop_stages.sh" "$@"
# (padding: a bash that was already running the earlier, longer version of this file resumes at byte 1856, inside these comment lines)
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
###################################################################################################
