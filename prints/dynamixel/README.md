# Printed parts

> **These are the print files for the all-Dynamixel duck only.** Each duck has its own parts, prints and BOM, and they don't mix. Other ducks: [HD-1910](../hd1910/README.md) · [all-Feetech](../feetech/README.md) · [hybrid](../hybrid/README.md) · [hobby-servo](../hobby/README.md) · [nano](../nano/README.md). <!-- variant banner -->

From `python -I tools/export_prints.py`, in millimetres: every part, left and right, already turned the way it should print, its long overhangs down
(tools/printable.py chooses). Pockets are cut 0.3 mm over each bought part and bearing seats 0.1 mm over. None has been test printed: print one joint first.

| Part | File | Size on the bed (mm) | Volume (cm3) | Material | Overhang to support (mm2) |
|---|---|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 37 x 26 x 3 | 1.5 | PLA | 0 (none) |
| L yaw bracket | L_yaw_bracket.stl | 15 x 28 x 22 | 5.1 | PLA | 241 |
| L roll bracket | L_roll_bracket.stl | 35 x 31 x 19 | 4.9 | PLA | 214 |
| L thigh frame | L_thigh_frame.stl | 51 x 66 x 34 | 10.5 | PLA | 2118 |
| L hip pitch lid | L_hip_pitch_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| L knee lid | L_knee_lid.stl | 38 x 26 x 3 | 1.4 | PLA | 0 (none) |
| L thigh cover | L_thigh_cover.stl | 55 x 70 x 34 | 16.0 | PLA | 0 (none) |
| L shin | L_shin.stl | 38 x 32 x 23 | 5.9 | PLA | 399 |
| L shoe | L_shoe.stl | 58 x 44 x 26 | 13.1 | PLA | 89 |
| L sole | L_sole.stl | 58 x 44 x 12 | 25.7 | TPU 95A | 0 (none) |
| R hip yaw lid | R_hip_yaw_lid.stl | 37 x 26 x 3 | 1.5 | PLA | 0 (none) |
| R yaw bracket | R_yaw_bracket.stl | 15 x 28 x 22 | 5.1 | PLA | 241 |
| R roll bracket | R_roll_bracket.stl | 35 x 31 x 19 | 5.0 | PLA | 199 |
| R thigh frame | R_thigh_frame.stl | 51 x 66 x 34 | 10.5 | PLA | 2118 |
| R hip pitch lid | R_hip_pitch_lid.stl | 26 x 37 x 3 | 1.5 | PLA | 0 (none) |
| R knee lid | R_knee_lid.stl | 38 x 26 x 3 | 1.4 | PLA | 0 (none) |
| R thigh cover | R_thigh_cover.stl | 55 x 70 x 34 | 16.0 | PLA | 0 (none) |
| R shin | R_shin.stl | 38 x 32 x 23 | 5.9 | PLA | 399 |
| R shoe | R_shoe.stl | 58 x 44 x 26 | 13.1 | PLA | 89 |
| R sole | R_sole.stl | 58 x 44 x 12 | 25.7 | TPU 95A | 0 (none) |
| chassis | chassis.stl | 45 x 58 x 73 | 15.3 | PLA | 1050 |
| body shell | body_shell.stl | 38 x 74 x 98 | 22.4 | PLA | 1460 |
| neck column | neck_column.stl | 26 x 28 x 10 | 2.4 | PLA | 41 |
| head fork | head_fork.stl | 53 x 39 x 45 | 9.3 | PLA | 705 |
| head yaw sheet | head_yaw_sheet.stl | 37 x 26 x 4 | 0.7 | PLA | 0 (none) |
| head yaw bracket | head_yaw_bracket.stl | 28 x 37 x 26 | 5.4 | PLA | 161 |
| head yaw spacer | head_yaw_spacer.stl | 17 x 17 x 2 | 0.3 | PLA | 0 (none) |
| head lower shell | head_lower_shell.stl | 53 x 92 x 14 | 19.4 | PLA | 691 |
| head frame | head_frame.stl | 129 x 101 x 45 | 37.2 | PLA | 1297 |
| hood | hood.stl | 58 x 106 x 150 | 48.4 | PLA | 3368 |
| hinge sleeve | hinge_sleeve.stl | 9 x 9 x 7 | 0.2 | PLA | 0 (none) |
| jaw | jaw.stl | 88 x 106 x 43 | 29.4 | PLA | 939 |
| jaw soft insert | jaw_soft_insert.stl | 27 x 101 x 5 | 13.3 | TPU 95A | 0 (none) |
| mouth roof | mouth_roof.stl | 40 x 101 x 3 | 12.6 | TPU 95A | 3 |
| face | face.stl | 50 x 99 x 3 | 8.3 | PLA | 4173 |
| eye ring | eye_ring.stl | 34 x 34 x 11 | 7.4 | PLA | 0 (none) |
| eye iris | eye_iris.stl | 20 x 20 x 9 | 1.9 | PLA | 0 (none) |

The head frame prints in orange, in one filament: only its rim shows below the hood. The hood is modelled in two colours, a white top and an orange 5 mm band at its rim: one STL, so print it white and paint the band, or split the colour in a multi-material slicer.
A part with an overhang figure needs support or a bridge there; tools/printable.py counts faces, not a slicer, so it overstates short bridges. Check each in your slicer.


## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin`, with 1 XL330-M288, 1 6703ZZ,
its M2 screws. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
