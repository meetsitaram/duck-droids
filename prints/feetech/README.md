# Printed parts

> **These are the print files for the all-Feetech duck only.** Each duck has its own parts, prints and BOM, and they don't mix. Other ducks: [all-Dynamixel](../dynamixel/README.md) · [HD-1910](../hd1910/README.md) · [hybrid](../hybrid/README.md) · [hobby-servo](../hobby/README.md). <!-- variant banner -->

From `python -I tools/export_prints.py`, in millimetres: every part, left and right, already turned the way it should print, its long overhangs down
(tools/printable.py chooses). Pockets are cut 0.3 mm over each bought part and bearing seats 0.1 mm over. None has been test printed: print one joint first.

| Part | File | Size on the bed (mm) | Volume (cm3) | Material | Overhang to support (mm2) |
|---|---|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 6 x 31 x 51 | 2.9 | PLA | 113 |
| L yaw bracket | L_yaw_bracket.stl | 62 x 30 x 41 | 16.5 | PLA | 579 |
| L hip roll lid | L_hip_roll_lid.stl | 6 x 29 x 51 | 2.5 | PLA | 113 |
| L roll bracket | L_roll_bracket.stl | 23 x 36 x 37 | 5.7 | PLA | 174 |
| L thigh frame | L_thigh_frame.stl | 81 x 46 x 61 | 18.3 | PLA | 1375 |
| L hip pitch lid | L_hip_pitch_lid.stl | 31 x 51 x 6 | 3.0 | PLA | 167 |
| L knee lid | L_knee_lid.stl | 51 x 31 x 6 | 2.9 | PLA | 167 |
| L thigh cover | L_thigh_cover.stl | 67 x 87 x 46 | 25.7 | PLA | 44 |
| L shin | L_shin.stl | 79 x 42 x 31 | 12.8 | PLA | 832 |
| L shoe | L_shoe.stl | 29 x 53 x 69 | 15.7 | PLA | 708 |
| L sole | L_sole.stl | 15 x 53 x 69 | 40.8 | TPU 95A | 478 |
| L inner ear | L_inner_ear.stl | 29 x 48 x 4 | 2.5 | PLA | 0 (none) |
| R hip yaw lid | R_hip_yaw_lid.stl | 6 x 31 x 51 | 2.9 | PLA | 108 |
| R yaw bracket | R_yaw_bracket.stl | 62 x 30 x 41 | 16.5 | PLA | 579 |
| R hip roll lid | R_hip_roll_lid.stl | 6 x 29 x 51 | 2.5 | PLA | 113 |
| R roll bracket | R_roll_bracket.stl | 23 x 36 x 37 | 5.7 | PLA | 174 |
| R thigh frame | R_thigh_frame.stl | 81 x 46 x 61 | 18.3 | PLA | 1375 |
| R hip pitch lid | R_hip_pitch_lid.stl | 31 x 51 x 6 | 3.0 | PLA | 167 |
| R knee lid | R_knee_lid.stl | 51 x 31 x 6 | 2.9 | PLA | 167 |
| R thigh cover | R_thigh_cover.stl | 67 x 87 x 46 | 25.7 | PLA | 44 |
| R shin | R_shin.stl | 79 x 42 x 31 | 12.8 | PLA | 832 |
| R shoe | R_shoe.stl | 29 x 53 x 69 | 15.7 | PLA | 708 |
| R sole | R_sole.stl | 15 x 53 x 69 | 40.8 | TPU 95A | 477 |
| R inner ear | R_inner_ear.stl | 29 x 48 x 4 | 2.5 | PLA | 0 (none) |
| chassis | chassis.stl | 52 x 101 x 65 | 55.5 | PLA | 3314 |
| body shell | body_shell.stl | 49 x 80 x 94 | 28.2 | PLA | 1203 |
| neck column | neck_column.stl | 46 x 31 x 49 | 11.3 | PLA | 422 |
| neck lid | neck_lid.stl | 9 x 31 x 3 | 0.7 | PLA | 0 (none) |
| head pitch lid | head_pitch_lid.stl | 9 x 31 x 3 | 0.8 | PLA | 0 (none) |
| head fork | head_fork.stl | 73 x 54 x 48 | 18.8 | PLA | 838 |
| head yaw sheet | head_yaw_sheet.stl | 51 x 31 x 4 | 1.3 | PLA | 167 |
| head yaw bracket | head_yaw_bracket.stl | 38 x 41 x 48 | 13.7 | PLA | 469 |
| head roll lid | head_roll_lid.stl | 31 x 51 x 6 | 3.0 | PLA | 167 |
| head roll spacer | head_roll_spacer.stl | 20 x 20 x 3 | 0.7 | PLA | 0 (none) |
| head frame | head_frame.stl | 181 x 131 x 65 | 84.6 | PLA | 7206 |
| hood | hood.stl | 73 x 135 x 192 | 79.4 | PLA | 5100 |
| jaw | jaw.stl | 48 x 135 x 108 | 47.3 | PLA | 1221 |
| jaw soft insert | jaw_soft_insert.stl | 35 x 131 x 5 | 22.7 | TPU 95A | 0 (none) |
| mouth roof | mouth_roof.stl | 49 x 131 x 3 | 19.9 | TPU 95A | 4 |
| face | face.stl | 65 x 129 x 3 | 14.3 | PLA | 89 |
| eye ring | eye_ring.stl | 44 x 44 x 14 | 6.5 | PLA | 0 (none) |
| eye iris | eye_iris.stl | 25 x 25 x 6 | 2.2 | PLA | 0 (none) |

The head frame prints in orange, in one filament: only its rim shows below the hood. The hood is modelled in two colours, a white top and an orange 5 mm band at its rim: one STL, so print it white and paint the band, or split the colour in a multi-material slicer.
A part with an overhang figure needs support or a bridge there; tools/printable.py counts faces, not a slicer, so it overstates short bridges. Check each in your slicer.


## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin`, with 1 STS3215-C044, 1 6704ZZ,
6 M2 x 6, 2 M2 x 8 and 4 M3 x 10. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
