"""Read an rsl_rl training log: the last iteration's numbers, and whether the run is stuck.

  python log_progress.py LOG [--stuck-after 500]
prints one line: "it N/M ep_len X reward Y [stage S]", then "STUCK" on a second line if neither the mean episode length nor the mean reward has
reached a new best in the last --stuck-after iterations (a run flat at the episode's full length is still improving its reward, so not stuck).
Plain python, no trainer imports.
"""
import re
import sys


def main():
    log = sys.argv[1]
    after = int(sys.argv[sys.argv.index("--stuck-after") + 1]) if "--stuck-after" in sys.argv else 500
    t = open(log, encoding="utf-8", errors="replace").read()
    parts = re.split(r"Learning iteration (\d+)/(\d+)", t)
    rows = []
    for i in range(1, len(parts) - 2, 3):
        b = parts[i + 2]
        g = lambda k: (lambda m: float(m.group(1)) if m else None)(re.search(re.escape(k) + r":\s+(-?[\d.]+(?:e-?\d+)?)", b))
        rows.append((int(parts[i]), int(parts[i + 1]), g("Mean episode length"), g("Mean reward"), g("Curriculum/slop_servos_pushes/stage")))
    rows = [r for r in rows if r[2] is not None]
    if not rows:
        print("no iterations yet")
        return
    it, tot, ep, rw, stage = rows[-1]
    print(f"it {it}/{tot} ep_len {ep:.0f} reward {rw:.2f}" + (f" stage {stage:.0f}" if stage is not None else ""))
    best_ep = best_rw = -1e9
    last_best = rows[0][0]
    for r in rows:
        if r[2] > best_ep * 1.02 + 1:
            best_ep, last_best = r[2], r[0]
        if r[3] is not None and r[3] > best_rw + 0.02 * abs(best_rw) + 0.01:
            best_rw, last_best = r[3], r[0]
    if it - last_best >= after:
        print("STUCK")


if __name__ == "__main__":
    main()
