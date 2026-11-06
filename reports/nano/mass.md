# Mass model

Bottom-up: every part from its material and shape (`tools/mass_model.py`, materials in `spec/robot.py`), a 3 % wiring allowance per link on its frames.

**Total 0.37 kg** (microduck: 0.8 kg).

| material | kg | share |
|---|---|---|
| pla | 0.16 | 44 % |
| actuator | 0.14 | 38 % |
| electronics | 0.04 | 12 % |
| steel | 0.02 | 5 % |
| tpu | 0.01 | 2 % |

| link | mass kg | budget kg (hand estimate) | CoM (m, world, zero pose) | principal inertia (kg m2) |
|---|---|---|---|---|
| L_knee_link | 0.02 | 0.00 | -0.031 +0.021 +0.031 | 0.0000 0.0000 0.0000 |
| R_knee_link | 0.02 | 0.00 | -0.031 -0.021 +0.031 | 0.0000 0.0000 0.0000 |
| L_foot | 0.01 | 0.00 | -0.020 +0.024 +0.005 | 0.0000 0.0000 0.0000 |
| R_foot | 0.01 | 0.00 | -0.020 -0.024 +0.005 | 0.0000 0.0000 0.0000 |
| L_hip_pitch_link | 0.03 | 0.00 | -0.019 +0.021 +0.068 | 0.0000 0.0000 0.0000 |
| R_hip_pitch_link | 0.03 | 0.00 | -0.019 -0.021 +0.068 | 0.0000 0.0000 0.0000 |
| L_hip_roll_link | 0.01 | 0.00 | +0.010 +0.018 +0.084 | 0.0000 0.0000 0.0000 |
| R_hip_roll_link | 0.01 | 0.00 | +0.010 -0.018 +0.084 | 0.0000 0.0000 0.0000 |
| L_hip_yaw_link | 0.02 | 0.00 | +0.004 +0.018 +0.108 | 0.0000 0.0000 0.0000 |
| R_hip_yaw_link | 0.02 | 0.00 | +0.004 -0.018 +0.108 | 0.0000 0.0000 0.0000 |
| trunk | 0.12 | 0.00 | -0.012 -0.002 +0.132 | 0.0000 0.0001 0.0002 |
| neck_link | 0.00 | 0.00 | +0.045 +0.000 +0.153 | 0.0000 0.0000 0.0000 |
| head | 0.05 | 0.00 | +0.070 +0.002 +0.175 | 0.0000 0.0000 0.0000 |
| beak_link | 0.00 | 0.00 | +0.096 +0.002 +0.158 | 0.0000 0.0000 0.0000 |
