"""The three servo recipes at one scale, for the README: python tools/render_recipes.py -> docs/images/recipes/<recipe>.png

Offline renders of each recipe's spec (spec/robot.py's RECIPES; generate the spec first, with MILLI_RECIPE set). Plain python.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'docs', 'images', 'recipes')
RECIPES = ('dynamixel', 'hybrid', 'feetech')
SIZE = 640                                         # pixels; the camera's scale and framing are the same in all three


def main():
    if len(sys.argv) > 1:
        import render_pose as RP
        RP.Scene().render({}, '34', SIZE, SIZE, 0.46, 0.215).save(os.path.join(OUT, sys.argv[1] + '.png'))
        return 0
    os.makedirs(OUT, exist_ok=True)
    for r in RECIPES:
        subprocess.run([sys.executable, os.path.abspath(__file__), r], check=True, env=dict(os.environ, MILLI_RECIPE=r))
        print(r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
