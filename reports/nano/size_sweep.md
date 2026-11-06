# The nano duck: size against torque

From `python -I tools/nano_sweep.py`. Each row is spec/nano_duck.py with its free lengths stretched (`NANO_STRETCH`); the servo cases set the rest.
Torque as a share of stall at about 5 V (SG90 0.157 N m, MG90S 0.177 N m: spec/actuators.json), from tools/checks.py's statics. The rule: under about 50 %.

| stretch | height (cm) | mass (g) | knees, crouch | hip roll, single leg x 1.5 | neck, standing | head pitch, standing |
|---|---|---|---|---|---|---|
| 1.00 | 20.6 | 370 | 32 % (0.057 N m) | 45 % (0.053 N m x 1.5) | 8 % (0.012 N m) | 8 % |
| 1.25 | 22.1 | 374 | 35 % (0.062 N m) | 46 % (0.054 N m x 1.5) | 8 % (0.013 N m) | 9 % |
| 1.50 | 23.7 | 378 | 38 % (0.066 N m) | 46 % (0.055 N m x 1.5) | 9 % (0.014 N m) | 9 % |
| 2.00 | 26.9 | 398 | 43 % (0.076 N m) | 49 % (0.058 N m x 1.5) | 10 % (0.016 N m) | 10 % |
| 2.50 | 30.0 | 428 | 51 % **over** (0.090 N m) | 53 % **over** (0.062 N m x 1.5) | 12 % (0.019 N m) | 12 % |

Heights under the first row's cannot be built in this layout: see spec/nano_duck.py's docstring. Only the first row is the checked design (tools/checks.py, assembly.py, buildable.py, printable.py at 0 failing);
the stretched rows are torque estimates, their shapes not checked, and their thin members would need thickening, which adds mass. A static estimate only: walking adds the dynamics, and a real SG90 sags under load before it stalls.

Chosen: stretch 1.0. The rule alone (the largest under 50 %) points to about 27 cm, microduck's own size, which isn't a palm-sized duck; 12-18 cm, the range asked for, is under what this layout can build, so the duck is the smallest it can.
