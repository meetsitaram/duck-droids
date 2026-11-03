# Printed parts

From `python -I tools/export_prints.py`, in millimetres, the left side; mirror them for the right. Not yet test printed.

| Part | File | Size (mm) | Solid volume (cm3) |
|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 51 x 31 x 6 | 3.2 |
| L yaw bracket | L_yaw_bracket.stl | 41 x 30 x 59 | 17.7 |
| L hip roll lid | L_hip_roll_lid.stl | 6 x 29 x 51 | 2.8 |
| L roll bracket | L_roll_bracket.stl | 37 x 33 x 23 | 4.5 |
| L thigh frame | L_thigh_frame.stl | 81 x 41 x 61 | 19.3 |
| L hip pitch lid | L_hip_pitch_lid.stl | 51 x 6 x 31 | 3.2 |
| L knee lid | L_knee_lid.stl | 31 x 6 x 51 | 3.2 |
| L thigh cover | L_thigh_cover.stl | 87 x 43 x 67 | 24.3 |
| L shin | L_shin.stl | 31 x 45 x 79 | 12.4 |
| L ankle lid | L_ankle_lid.stl | 25 x 3 x 9 | 0.6 |
| L shoe | L_shoe.stl | 69 x 53 x 29 | 15.2 |
| L sole | L_sole.stl | 69 x 53 x 15 | 43.8 |
| L inner ear | L_inner_ear.stl | 48 x 5 x 29 | 3.3 |
| chassis | chassis.stl | 96 x 63 x 42 | 36.9 |
| body shell | body_shell.stl | 98 x 80 x 44 | 30.2 |
| neck column | neck_column.stl | 26 x 34 x 35 | 6.4 |
| neck lid | neck_lid.stl | 26 x 3 x 5 | 0.2 |
| head pitch lid | head_pitch_lid.stl | 26 x 2 x 5 | 0.2 |
| head fork | head_fork.stl | 37 x 39 x 58 | 9.6 |
| head yaw sheet | head_yaw_sheet.stl | 37 x 26 x 4 | 0.9 |
| head yaw bracket | head_yaw_bracket.stl | 32 x 40 x 26 | 6.3 |
| head roll lid | head_roll_lid.stl | 3 x 37 x 26 | 1.5 |
| head frame | head_frame.stl | 125 x 94 x 43 | 43.1 |
| beak lid | beak_lid.stl | 5 x 2 x 23 | 0.2 |
| hood | hood.stl | 155 x 110 x 60 | 53.3 |
| jaw | jaw.stl | 105 x 110 x 43 | 36.7 |
| jaw soft insert | jaw_soft_insert.stl | 28 x 105 x 5 | 14.6 |
| mouth roof | mouth_roof.stl | 41 x 105 x 3 | 13.5 |

## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin` (about 32 cm3 solid), with 1 STS3215-C044, 1 6704ZZ,
6 M2 x 6, 2 M2 x 8 and 4 M3 x 10. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
