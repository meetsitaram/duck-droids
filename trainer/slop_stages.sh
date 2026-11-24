#!/bin/bash
# The stages of the two-stage walk (milli_slop_env_cfg.py in the trainer), and the night's skills. Called by train_slop.sh; run from the trainer's
# folder, environment active. Two walking policies come out, each an ONNX in pi/models with a JSON that says how to build its input (export_slop.py):
#   walk_imu    the stage-1 teacher's actor: IMU + joints + last action. For the duck with its Pi and IMU on board.
#   walk_blind  the stage-2 DAgger student: joints + last action, with history, and commands. Built from servo bus reads alone: for the duck
#               driven from a PC over the bus, with no IMU.
# Progress goes to OVERNIGHT.md in the trainer's folder, a line per step.
# The whole script is one { ... } block ending in exit: bash reads it all before running any of it, so editing this file can't upset a running copy.
{
set -e
export WANDB_MODE=offline PYTHONUTF8=1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/../pi/models
ENVS=${ENVS:-4096}
TEACHER_TASK=Mjlab-Velocity-Flat-Milli-Dynamixel-Slop
STUDENT_TASK=Mjlab-Velocity-Flat-Milli-Dynamixel-Slop-Student
BASELINE_TASK=Mjlab-Velocity-Flat-Milli-Dynamixel-Slop-EncoderPPO
# the night's skills after the walk (name task), each up to its own max_iterations, capped at SKILL_CAP
SKILLS="groundpick_beak:Mjlab-GroundPickBeak-Flat-Milli-Dynamixel sitstand:Mjlab-SitStand-Flat-Milli-Dynamixel kick_right:Mjlab-BallKickRight-Flat-Milli-Dynamixel kick_left:Mjlab-BallKickLeft-Flat-Milli-Dynamixel"
SKILL_CAP=${SKILL_CAP:-3000}
newest() { ls -d logs/rsl_rl/$1/20*/ 2>/dev/null | sort | tail -1; }      # dated run folders only (not a warm-start folder)
last_model() { ls "$1"model_*.pt | awk -F'model_' '{print $NF+0, $0}' | sort -n | tail -1 | cut -d' ' -f2; }
status() { echo "- $(date '+%m-%d %H:%M') $*" >> OVERNIGHT.md; echo "$*"; }
progress() { python "$HERE/log_progress.py" "$1" | head -1; }
evaluate() {   # task, checkpoint, name; pushes on, the same seed for every policy, so they meet the same robots and pushes
  python scripts/milli_eval.py "$2" --task "$1" --recipe dynamixel --model milli_dynamixel_realgain --envs 512 --seed 0 --out "eval_slop_$3.json" > "eval_slop_$3.txt" 2>&1
  grep -E "^(stand|forward|backward|sideways|turn) " "eval_slop_$3.txt" | sed "s/^/$3: /"
}
kill_tree() {  # an MSYS pid of a background `train`: the Windows process tree under it
  local w; w=$(cat /proc/$1/winpid 2>/dev/null || true)
  [ -n "$w" ] && taskkill //F //T //PID "$w" > /dev/null 2>&1 || kill "$1" 2> /dev/null || true
}
train_watched() {  # log, then the train command: runs it, and stops it if log_progress.py says STUCK (flat for 500 iterations)
  local log=$1; shift
  "$@" > "$log" 2>&1 &
  local pid=$!
  while kill -0 $pid 2> /dev/null; do
    sleep 120
    if python "$HERE/log_progress.py" "$log" 2> /dev/null | grep -q STUCK; then
      status "STUCK: $(progress "$log") in $log: stopped it, moving on"
      kill_tree $pid; sleep 10; return 0
    fi
  done
  wait $pid || status "exited with an error: $log (tail: $(tail -1 "$log" | tr -d '\r' | cut -c1-120))"
}
case "$1" in
  teacher)
    train $TEACHER_TASK --env.scene.num-envs $ENVS --agent.max_iterations ${ITERS:-3000} > train_slop_teacher.log 2>&1 ;;
  teacher-warm)      # [RUN_FOLDER] [CHECKPOINT]: the weights of logs/rsl_rl/milli_dynamixel_slop_teacher/RUN_FOLDER/CHECKPOINT, iterations and curricula from 0
    # (MICRODUCK_WARM_START, mdp.py Patch 5). The default: the 0.96 N m run's model_750 with its action std raised to at least 0.2 (a reset to 0.5
    # made the warm start fall more, not less: episodes 46 -> 31 steps over 100 iterations). (The trainer's --init-checkpoint flag doesn't fire on
    # Windows, where the program is train.exe: train_hook.py checks for "train".)
    status "walk teacher: warm start from ${2:-warmstart_750_std02}/${3:-model_750.pt}, curriculum on, train_slop_teacher.log"
    MICRODUCK_WARM_START=1 train $TEACHER_TASK --env.scene.num-envs $ENVS --agent.max_iterations ${ITERS:-3000} --agent.resume True \
      --agent.load_run "${2:-warmstart_750_std02}" --agent.load_checkpoint "${3:-model_750.pt}" > train_slop_teacher.log 2>&1
    status "walk teacher done: $(progress train_slop_teacher.log)" ;;
  student)
    T=${2:-$(last_model "$(newest milli_dynamixel_slop_teacher)")}
    status "walk student (DAgger, blind) from teacher $T: train_slop_student.log"
    MILLI_TEACHER_CKPT=$T train $STUDENT_TASK --env.scene.num-envs $ENVS --agent.max_iterations ${ITERS:-2000} > train_slop_student.log 2>&1
    status "walk student done: $(progress train_slop_student.log)" ;;
  baseline)
    status "baseline (encoder-only PPO): train_slop_baseline.log"
    train $BASELINE_TASK --env.scene.num-envs $ENVS --agent.max_iterations ${ITERS:-3000} > train_slop_baseline.log 2>&1
    status "baseline done: $(progress train_slop_baseline.log)" ;;
  export-imu)        # CKPT
    python "$HERE/export_slop.py" $TEACHER_TASK "$2" "$OUT/walk_imu.onnx" > export_slop_imu.log 2>&1 && status "exported $(tail -1 export_slop_imu.log)" ;;
  export-blind)      # CKPT TEACHER_CKPT
    MILLI_TEACHER_CKPT=$3 python "$HERE/export_slop.py" $STUDENT_TASK "$2" "$OUT/walk_blind.onnx" > export_slop_blind.log 2>&1 && status "exported $(tail -1 export_slop_blind.log)" ;;
  eval-pair)         # TEACHER_CKPT STUDENT_CKPT
    status "eval, pushes on, seed 0, 512 robots, 8 s per test (eval_slop_imu.txt, eval_slop_blind.txt):"
    evaluate $TEACHER_TASK "$2" imu | while read -r l; do status "  $l"; done
    MILLI_TEACHER_CKPT=$2 evaluate $STUDENT_TASK "$3" blind | while read -r l; do status "  $l"; done
    bash "$0" eval-table ;;
  eval-table)        # the evals so far, side by side, into OVERNIGHT.md
    { echo; echo "Walk evals, 512 robots, pushes on, seed 0, 8 s per command (up / speed error m/s / yaw rate error rad/s, over robots up after 2 s):"; echo
      args=""; for n in imu blind baseline; do [ -f "eval_slop_$n.json" ] && args="$args $n=eval_slop_$n.json"; done
      python "$HERE/eval_table.py" $args; echo; } >> OVERNIGHT.md ;;
  skills)            # [name:task ...]: each in turn, watched for a stall, exported to pi/models/<name>.onnx
    for nt in ${2:-$SKILLS}; do
      n=${nt%%:*}; t=${nt#*:}
      read -r exp mx < <(python -c "import mjlab_microduck.tasks; from mjlab.tasks.registry import load_rl_cfg; c = load_rl_cfg('$t'); print(c.experiment_name, c.max_iterations)" 2>/dev/null | tail -1)
      mx=${mx//[!0-9]/}; exp=${exp//[[:space:]]/}          # Windows python ends its lines in CR
      it=$(( mx < SKILL_CAP ? mx : SKILL_CAP ))
      status "skill $n: $t, $it iterations, train_skill_$n.log"
      train_watched "train_skill_$n.log" train "$t" --env.scene.num-envs $ENVS --agent.max_iterations $it
      ck=$(last_model "$(newest "$exp")" 2> /dev/null || true)
      status "skill $n ended: $(progress "train_skill_$n.log"), last checkpoint $ck"
      if [ -n "$ck" ]; then
        python scripts/export.py "$t" --checkpoint-file "$ck" --onnx-file "$OUT/$n.onnx" > "export_skill_$n.log" 2>&1 \
          && status "exported $OUT/$n.onnx" || status "export of $n failed: export_skill_$n.log"
      fi
    done ;;
  after-teacher)
    # waits for the running teacher's last checkpoint, then: export it, train the blind student, export it, evaluate both side by side, the skills,
    # then the baseline. A failed step is noted in OVERNIGHT.md and the queue carries on.
    set +e
    R=$(newest milli_dynamixel_slop_teacher)
    T=${R}model_$(( ${ITERS:-3000} - 1 )).pt
    status "queue: waiting for $T"
    while [ ! -f "$T" ]; do sleep 60; done
    sleep 30                                   # let the save finish
    bash "$0" export-imu "$T" || status "export of walk_imu failed: export_slop_imu.log"
    bash "$0" student "$T"
    S=$(last_model "$(newest milli_dynamixel_slop_student)")
    bash "$0" export-blind "$S" "$T" || status "export of walk_blind failed: export_slop_blind.log"
    bash "$0" eval-pair "$T" "$S" || status "eval failed: eval_slop_*.txt"
    bash "$0" skills
    bash "$0" baseline
    evaluate $BASELINE_TASK "$(last_model "$(newest milli_dynamixel_slop_encoder_ppo)")" baseline | while read -r l; do status "  $l"; done
    bash "$0" eval-table
    status "queue finished" ;;
  *) echo "usage: $0 teacher | teacher-warm [RUN CKPT] | student [CKPT] | baseline | export-imu CKPT | export-blind CKPT TEACHER | eval-pair TEACHER STUDENT | eval-table | skills [name:task ...] | after-teacher"; exit 1 ;;
esac
exit
}
