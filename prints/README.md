# Printed parts

From `python -I tools/export_prints.py`, in millimetres: every part, left and right, already turned the way it should print, its long overhangs down
(tools/printable.py chooses). Pockets are cut 0.3 mm over each bought part and bearing seats 0.1 mm over. None has been test printed: print one joint first.

| Part | File | Size on the bed (mm) | Volume (cm3) | Material | Overhang to support (mm2) |
|---|---|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 51 x 31 x 6 | 3.0 | PLA | 167 |
| L yaw bracket | L_yaw_bracket.stl | 59 x 30 x 41 | 16.0 | PLA | 430 |
| L hip roll lid | L_hip_roll_lid.stl | 51 x 29 x 6 | 2.5 | PLA | 167 |
| L roll bracket | L_roll_bracket.stl | 23 x 33 x 37 | 3.8 | PLA | 74 |
| L thigh frame | L_thigh_frame.stl | 81 x 46 x 61 | 18.1 | PLA | 1462 |
| L hip pitch lid | L_hip_pitch_lid.stl | 31 x 6 x 51 | 2.7 | PLA | 134 |
| L knee lid | L_knee_lid.stl | 31 x 6 x 51 | 2.7 | PLA | 152 |
| L thigh cover | L_thigh_cover.stl | 67 x 87 x 46 | 26.4 | PLA | 421 |
| L shin | L_shin.stl | 79 x 45 x 31 | 11.7 | PLA | 712 |
| L ankle lid | L_ankle_lid.stl | 9 x 25 x 3 | 0.6 | PLA | 0 (none) |
| L shoe | L_shoe.stl | 29 x 53 x 69 | 14.7 | PLA | 683 |
| L sole | L_sole.stl | 15 x 53 x 69 | 40.8 | TPU 95A | 480 |
| L inner ear | L_inner_ear.stl | 29 x 48 x 5 | 2.7 | PLA | 52 |
| R hip yaw lid | R_hip_yaw_lid.stl | 51 x 31 x 6 | 3.0 | PLA | 167 |
| R yaw bracket | R_yaw_bracket.stl | 59 x 30 x 41 | 16.0 | PLA | 430 |
| R hip roll lid | R_hip_roll_lid.stl | 51 x 29 x 6 | 2.5 | PLA | 167 |
| R roll bracket | R_roll_bracket.stl | 23 x 33 x 37 | 3.8 | PLA | 74 |
| R thigh frame | R_thigh_frame.stl | 81 x 46 x 61 | 18.1 | PLA | 1462 |
| R hip pitch lid | R_hip_pitch_lid.stl | 31 x 6 x 51 | 2.7 | PLA | 134 |
| R knee lid | R_knee_lid.stl | 31 x 6 x 51 | 2.7 | PLA | 152 |
| R thigh cover | R_thigh_cover.stl | 67 x 87 x 46 | 26.4 | PLA | 421 |
| R shin | R_shin.stl | 79 x 45 x 31 | 11.7 | PLA | 712 |
| R ankle lid | R_ankle_lid.stl | 9 x 25 x 3 | 0.6 | PLA | 0 (none) |
| R shoe | R_shoe.stl | 29 x 53 x 69 | 14.7 | PLA | 683 |
| R sole | R_sole.stl | 15 x 53 x 69 | 40.8 | TPU 95A | 479 |
| R inner ear | R_inner_ear.stl | 29 x 48 x 5 | 2.7 | PLA | 52 |
| chassis | chassis.stl | 49 x 97 x 76 | 38.7 | PLA | 3284 |
| body shell | body_shell.stl | 49 x 80 x 98 | 32.4 | PLA | 2534 |
| neck column | neck_column.stl | 35 x 26 x 34 | 5.3 | PLA | 244 |
| neck lid | neck_lid.stl | 5 x 26 x 3 | 0.2 | PLA | 0 (none) |
| head pitch lid | head_pitch_lid.stl | 5 x 26 x 2 | 0.2 | PLA | 0 (none) |
| head fork | head_fork.stl | 58 x 39 x 37 | 9.3 | PLA | 440 |
| head yaw sheet | head_yaw_sheet.stl | 37 x 26 x 4 | 0.9 | PLA | 0 (none) |
| head yaw bracket | head_yaw_bracket.stl | 26 x 40 x 32 | 5.8 | PLA | 209 |
| head roll lid | head_roll_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| head frame | head_frame.stl | 123 x 94 x 50 | 44.0 | PLA | 3932 |
| beak lid | beak_lid.stl | 20 x 5 x 2 | 0.2 | PLA | 0 (none) |
| beak crank | beak_crank.stl | 24 x 20 x 14 | 1.3 | PLA | 0 (none) |
| beak rod | beak_rod.stl | 13 x 44 x 3 | 0.7 | PLA | 0 (none) |
| hood | hood.stl | 60 x 110 x 155 | 53.7 | PLA | 2862 |
| jaw | jaw.stl | 43 x 113 x 105 | 37.2 | PLA | 1046 |
| jaw soft insert | jaw_soft_insert.stl | 28 x 105 x 5 | 14.3 | TPU 95A | 0 (none) |
| mouth roof | mouth_roof.stl | 41 x 105 x 3 | 13.5 | TPU 95A | 3 |
| face | face.stl | 52 x 103 x 3 | 9.1 | PLA | 45 |
| eye ring | eye_ring.stl | 35 x 35 x 11 | 8.3 | PLA | 0 (none) |
| eye iris | eye_iris.stl | 20 x 20 x 9 | 2.2 | PLA | 0 (none) |

The hood is modelled in two colours, a white top and an orange 5 mm band at its rim: one STL, so print it white and paint the band, or split the colour in a multi-material slicer.
A part with an overhang figure needs support or a bridge there; tools/printable.py counts faces, not a slicer, so it overstates short bridges. Check each in your slicer.


## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin` (about 32 cm3 solid), with 1 STS3215-C044, 1 6704ZZ,
6 M2 x 6, 2 M2 x 8 and 4 M3 x 10. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
