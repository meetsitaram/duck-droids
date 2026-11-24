"""The walk evals side by side, as a markdown table: python eval_table.py NAME=EVAL.json [NAME=EVAL.json ...]
For each command: robots still up at the end (pushes on, same seed), mean speed error (m/s, in the plane, body frame) and mean yaw rate error
(rad/s), over the robots still up after the first 2 s. From scripts/milli_eval.py's --out files. Plain python."""
import json
import sys


def main():
    evals = [(a.split("=", 1)[0], json.load(open(a.split("=", 1)[1]))["tests"]) for a in sys.argv[1:]]
    tests = list(evals[0][1])
    print("| command (vx, vy, wz) | " + " | ".join(f"{n}: up / speed err / yaw err" for n, _ in evals) + " |")
    print("|---|" + "---|" * len(evals))
    for t in tests:
        c = evals[0][1][t].get("command")
        cells = []
        for _, e in evals:
            r = e.get(t)
            cells.append("-" if r is None else f"{r['survived'] * 100:.0f} % / {r.get('lin_err', float('nan')):.3f} / {r.get('yaw_err', float('nan')):.2f}")
        print(f"| {t} ({', '.join(f'{v:g}' for v in c)}) | " + " | ".join(cells) + " |" if c else f"| {t} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
