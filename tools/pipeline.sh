#!/bin/bash
# The whole chain for one duck, from whichever worktree this is in. Takes its turn at Fusion and at rendering if TEAM_DIR is set.
#
#   MILLI_RECIPE=hd1910 AGENT=hd1910 bash tools/pipeline.sh gates     offline checks, docs, prints from the spec. Free: run it as often as you like
#   ... pipeline.sh fusion    linked Fusion build, prints from Fusion, audit: 10 min the first time, then 1-3 min, as it rebuilds only the links that changed
#   ... pipeline.sh final     the one-document Fusion build, for the repo's .f3d (about 12 min). Milestones only
#   ... pipeline.sh reveal    the one-document build and the 30-second reveal's frames, in one turn (about 40 min)
#   ... pipeline.sh video     the 5-minute build and the guide's clips (about 10 min; needs Fusion's bodies from `fusion` or `reveal`)
#
# Stops at the first failing gate. Reads the whole of each check's output, as a failure isn't always on its last line.
RECIPE=${MILLI_RECIPE:?set MILLI_RECIPE}
AGENT=${AGENT:-$RECIPE}
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8 MILLI_RECIPE=$RECIPE
PY=${PY:-/c/Users/meets/.venvs/duck/Scripts/python.exe}
TEAM=${TEAM:-$HOME/.claude/skills/agentic-team/scripts/team.py}
D=docs/images/assembly/$RECIPE
WORK=${TEMP:-/tmp}/pipeline_$RECIPE
mkdir -p "$WORK"
HELD=

take() {   # resource, minutes, why: waits its turn, if there's a team
  [ -n "$TEAM_DIR" ] || return 0
  while true; do
    "$PY" "$TEAM" wait "$1" --dir "$TEAM_DIR" --agent "$AGENT" --minutes "$2" --why "$3" --priority "${PRIORITY:-1}" --timeout 300
    rc=$?
    [ $rc -eq 0 ] && { HELD=$1; return 0; }
    [ $rc -eq 3 ] || { echo "scheduler error $rc"; exit 1; }
  done
}
give() {
  [ -n "$TEAM_DIR" ] && [ -n "$HELD" ] && "$PY" "$TEAM" release "$HELD" --dir "$TEAM_DIR" --agent "$AGENT"
  HELD=
}
trap give EXIT

gate() {   # name, command
  n=$1; shift
  s=$(date +%s)
  out=$("$@" 2>&1); rc=$?
  last=$(echo "$out" | tail -1 | cut -c1-150)
  echo "[$n] rc=$rc $(( $(date +%s) - s )) s: $last"
  if [ $rc -ne 0 ] || echo "$out" | grep -qE "(^|[ ,])[1-9][0-9]* failing"; then
    echo "$out" | grep -iE "fail|error|Traceback" | head -25 | cut -c1-220
    echo "STOPPED at $n"
    exit 1
  fi
}

gates() {
  gate spec "$PY" -I spec/robot.py
  gate checks "$PY" -I tools/checks.py
  gate assembly "$PY" -I tools/assembly.py
  gate buildable "$PY" -I tools/buildable.py
  gate docs "$PY" -I tools/make_docs.py
  gate export "$PY" -I tools/export_prints.py
  gate printable "$PY" -I tools/printable.py
  gate beak "$PY" -I tools/beak_linkage.py
  gate mass "$PY" -I tools/mass_model.py
}

build() {
  gate verify_write "$PY" -I tools/verify_fusion.py write
  sed 's/^KEEP_OPEN = False/KEEP_OPEN = True/' cad/fusion/full_build.py > "$WORK/fb_open.py"
  s=$(date +%s)
  "$PY" -I tools/fusion_call.py "$WORK/fb_open.py" --write --recipe "$RECIPE" 2>&1 | tail -14 | cut -c1-220
  echo "[fusion build] $(( $(date +%s) - s )) s"
  gate prints "$PY" -I tools/prints_from_fusion.py
  gate audit "$PY" -I tools/audit_prints.py
  gate compare "$PY" -I tools/verify_fusion.py compare
}

linked() {
  gate verify_write "$PY" -I tools/verify_fusion.py write
  s=$(date +%s)
  "$PY" -I tools/fusion_call.py cad/fusion/linked_build.py --write --recipe "$RECIPE" 2>&1 | grep -v "bodies, " | tail -12 | cut -c1-240
  echo "[linked build] $(( $(date +%s) - s )) s"
  gate prints "$PY" -I tools/prints_from_fusion.py
  gate audit "$PY" -I tools/audit_prints.py
  gate compare "$PY" -I tools/verify_fusion.py compare
}

case $1 in
  gates)
    gates
    ;;
  fusion)
    gates
    take fusion "${FUSION_MIN:-5}" "$RECIPE linked build"
    linked
    ;;
  final)
    gates
    take fusion 15 "$RECIPE one-document build"
    build
    ;;
  reveal)
    gates
    take fusion 40 "$RECIPE build and reveal frames"
    build
    for a in 0 150 300 450 600 750; do
      b=$((a + 149))
      [ -n "$TEAM_DIR" ] && "$PY" "$TEAM" renew fusion --dir "$TEAM_DIR" --agent "$AGENT" --minutes 20
      sed "s/^FIRST, LAST = 0, 2/FIRST, LAST = $a, $b/" cad/fusion/reveal_frames.py > "$WORK/rv.py"
      "$PY" -I tools/fusion_call.py "$WORK/rv.py" --write 2>&1 | tail -1 | cut -c1-120
    done
    "$PY" -I tools/reveal_video.py 2>&1 | tail -1 | cut -c1-140      # the frames' folder is shared: join them before giving Fusion up
    give
    FF=$("$PY" -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())")
    "$FF" -y -loglevel error -i "$D/reveal_30s.mp4" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart "$WORK/reveal.mp4" && cp "$WORK/reveal.mp4" "$D/reveal_30s.mp4"
    "$FF" -y -loglevel error -i "$D/reveal_30s.mp4" -vf "fps=12,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" "$D/reveal.gif"
    ls -la "$D/reveal_30s.mp4" "$D/reveal.gif"
    ;;
  video)
    take render 10 "$RECIPE 5-minute build and clips"
    gate floaters "$PY" tools/video_floaters.py
    "$PY" tools/render_pov_video.py 2>&1 | grep -v "^dry" | tail -3 | cut -c1-150
    "$PY" tools/cut_clips.py 2>&1 | tail -3 | cut -c1-110
    FF=$("$PY" -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())")
    "$FF" -y -loglevel error -i "$D/build_5min.mp4" -c:v libx264 -preset medium -crf 24 -pix_fmt yuv420p -movflags +faststart "$WORK/build.mp4" && cp "$WORK/build.mp4" "$D/build_5min.mp4"
    "$PY" -I tools/make_docs.py | tail -1 | cut -c1-70
    ls -la "$D/build_5min.mp4"
    ;;
  *)
    echo "gates, fusion, final, reveal or video"
    exit 2
    ;;
esac
echo "PIPELINE $1 DONE"
