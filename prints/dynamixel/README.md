# Printed parts

From `python -I tools/export_prints.py`, in millimetres: every part, left and right, already turned the way it should print, its long overhangs down
(tools/printable.py chooses). Pockets are cut 0.3 mm over each bought part and bearing seats 0.1 mm over. None has been test printed: print one joint first.

| Part | File | Size on the bed (mm) | Volume (cm3) | Material | Overhang to support (mm2) |
|---|---|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 37 x 26 x 3 | 1.5 | PLA | 0 (none) |
| L yaw bracket | L_yaw_bracket.stl | 48 x 25 x 29 | 8.2 | PLA | 196 |
| L hip roll lid | L_hip_roll_lid.stl | 37 x 24 x 3 | 1.2 | PLA | 0 (none) |
| L roll bracket | L_roll_bracket.stl | 19 x 31 x 30 | 3.5 | PLA | 108 |
| L thigh frame | L_thigh_frame.stl | 51 x 66 x 34 | 10.5 | PLA | 2118 |
| L hip pitch lid | L_hip_pitch_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| L knee lid | L_knee_lid.stl | 37 x 26 x 3 | 1.4 | PLA | 0 (none) |
| L thigh cover | L_thigh_cover.stl | 55 x 70 x 34 | 16.0 | PLA | 0 (none) |
| L shin | L_shin.stl | 66 x 32 x 21 | 6.5 | PLA | 307 |
| L shoe | L_shoe.stl | 30 x 43 x 58 | 11.5 | PLA | 395 |
| L sole | L_sole.stl | 13 x 44 x 58 | 24.8 | TPU 95A | 347 |
| L inner ear | L_inner_ear.stl | 30 x 42 x 4 | 2.2 | PLA | 0 (none) |
| R hip yaw lid | R_hip_yaw_lid.stl | 37 x 26 x 3 | 1.5 | PLA | 0 (none) |
| R yaw bracket | R_yaw_bracket.stl | 48 x 25 x 29 | 8.2 | PLA | 196 |
| R hip roll lid | R_hip_roll_lid.stl | 37 x 24 x 3 | 1.2 | PLA | 0 (none) |
| R roll bracket | R_roll_bracket.stl | 19 x 31 x 30 | 3.5 | PLA | 108 |
| R thigh frame | R_thigh_frame.stl | 51 x 66 x 34 | 10.5 | PLA | 2118 |
| R hip pitch lid | R_hip_pitch_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| R knee lid | R_knee_lid.stl | 37 x 26 x 3 | 1.4 | PLA | 0 (none) |
| R thigh cover | R_thigh_cover.stl | 55 x 70 x 34 | 16.0 | PLA | 0 (none) |
| R shin | R_shin.stl | 66 x 32 x 21 | 6.5 | PLA | 307 |
| R shoe | R_shoe.stl | 30 x 43 x 58 | 11.5 | PLA | 395 |
| R sole | R_sole.stl | 13 x 44 x 58 | 24.8 | TPU 95A | 347 |
| R inner ear | R_inner_ear.stl | 30 x 42 x 4 | 2.2 | PLA | 0 (none) |
| chassis | chassis.stl | 38 x 53 x 84 | 27.8 | PLA | 2114 |
| body shell | body_shell.stl | 38 x 74 x 85 | 22.1 | PLA | 1516 |
| neck column | neck_column.stl | 26 x 28 x 27 | 3.6 | PLA | 198 |
| neck lid | neck_lid.stl | 5 x 26 x 3 | 0.2 | PLA | 0 (none) |
| head pitch lid | head_pitch_lid.stl | 5 x 26 x 2 | 0.2 | PLA | 1 |
| head fork | head_fork.stl | 55 x 39 x 37 | 9.1 | PLA | 408 |
| head yaw sheet | head_yaw_sheet.stl | 37 x 26 x 4 | 0.8 | PLA | 0 (none) |
| head yaw bracket | head_yaw_bracket.stl | 28 x 29 x 40 | 5.7 | PLA | 218 |
| head roll lid | head_roll_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| head roll spacer | head_roll_spacer.stl | 16 x 16 x 2 | 0.3 | PLA | 0 (none) |
| head roll rear spacer | head_roll_rear_spacer.stl | 16 x 16 x 2 | 0.4 | PLA | 0 (none) |
| head frame | head_frame.stl | 141 x 101 x 59 | 54.2 | PLA | 5470 |
| hood | hood.stl | 58 x 106 x 150 | 48.7 | PLA | 2919 |
| jaw | jaw.stl | 88 x 106 x 42 | 29.6 | PLA | 925 |
| jaw soft insert | jaw_soft_insert.stl | 27 x 101 x 5 | 13.3 | TPU 95A | 0 (none) |
| mouth roof | mouth_roof.stl | 40 x 101 x 3 | 12.6 | TPU 95A | 15 |
| face | face.stl | 50 x 99 x 3 | 8.3 | PLA | 40 |
| eye ring | eye_ring.stl | 34 x 34 x 11 | 7.4 | PLA | 0 (none) |
| eye iris | eye_iris.stl | 20 x 20 x 9 | 1.9 | PLA | 0 (none) |

The head frame prints in orange, in one filament: only its rim shows below the hood. The hood is modelled in two colours, a white top and an orange 5 mm band at its rim: one STL, so print it white and paint the band, or split the colour in a multi-material slicer.
A part with an overhang figure needs support or a bridge there; tools/printable.py counts faces, not a slicer, so it overstates short bridges. Check each in your slicer.


## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin`, with 1 XL330-M288, 1 MR2216ZZ,
its M2 screws. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
