# Printed parts

> **These are the print files for the hobby-servo duck only.** Each duck has its own parts, prints and BOM, and they don't mix. Other ducks: [all-Dynamixel](../dynamixel/README.md) · [HD-1910](../hd1910/README.md) · [all-Feetech](../feetech/README.md) · [hybrid](../hybrid/README.md). <!-- variant banner -->

From `python -I tools/export_prints.py`, in millimetres: every part, left and right, already turned the way it should print, its long overhangs down
(tools/printable.py chooses). Pockets are cut 0.3 mm over each bought part and bearing seats 0.1 mm over. None has been test printed: print one joint first.

| Part | File | Size on the bed (mm) | Volume (cm3) | Material | Overhang to support (mm2) |
|---|---|---|---|---|---|
| L hip yaw lid | L_hip_yaw_lid.stl | 11 x 31 x 53 | 3.9 | PLA | 135 |
| L yaw bracket | L_yaw_bracket.stl | 65 x 27 x 40 | 18.3 | PLA | 680 |
| L hip roll lid | L_hip_roll_lid.stl | 11 x 29 x 53 | 3.5 | PLA | 117 |
| L roll bracket | L_roll_bracket.stl | 23 x 33 x 40 | 4.7 | PLA | 78 |
| L thigh frame | L_thigh_frame.stl | 66 x 45 x 86 | 38.5 | PLA | 3286 |
| L hip pitch lid | L_hip_pitch_lid.stl | 31 x 11 x 53 | 3.9 | PLA | 114 |
| L knee lid | L_knee_lid.stl | 31 x 10 x 53 | 4.0 | PLA | 112 |
| L thigh cover | L_thigh_cover.stl | 69 x 89 x 48 | 23.9 | PLA | 111 |
| L shin | L_shin.stl | 91 x 45 x 30 | 20.9 | PLA | 1148 |
| L shoe | L_shoe.stl | 29 x 57 x 69 | 17.0 | PLA | 688 |
| L sole | L_sole.stl | 15 x 58 x 69 | 44.7 | TPU 95A | 507 |
| L inner ear | L_inner_ear.stl | 29 x 48 x 4 | 2.5 | PLA | 0 (none) |
| R hip yaw lid | R_hip_yaw_lid.stl | 11 x 31 x 53 | 3.9 | PLA | 135 |
| R yaw bracket | R_yaw_bracket.stl | 65 x 27 x 40 | 18.3 | PLA | 680 |
| R hip roll lid | R_hip_roll_lid.stl | 11 x 29 x 53 | 3.5 | PLA | 117 |
| R roll bracket | R_roll_bracket.stl | 23 x 33 x 40 | 4.7 | PLA | 78 |
| R thigh frame | R_thigh_frame.stl | 66 x 45 x 86 | 38.5 | PLA | 3286 |
| R hip pitch lid | R_hip_pitch_lid.stl | 31 x 11 x 53 | 3.9 | PLA | 114 |
| R knee lid | R_knee_lid.stl | 31 x 10 x 53 | 4.0 | PLA | 112 |
| R thigh cover | R_thigh_cover.stl | 69 x 89 x 48 | 23.9 | PLA | 111 |
| R shin | R_shin.stl | 91 x 45 x 30 | 20.9 | PLA | 1148 |
| R shoe | R_shoe.stl | 29 x 57 x 69 | 17.0 | PLA | 688 |
| R sole | R_sole.stl | 15 x 58 x 69 | 44.7 | TPU 95A | 539 |
| R inner ear | R_inner_ear.stl | 29 x 48 x 4 | 2.5 | PLA | 0 (none) |
| chassis | chassis.stl | 67 x 76 x 112 | 67.4 | PLA | 5324 |
| body shell | body_shell.stl | 72 x 80 x 97 | 40.2 | PLA | 1756 |
| neck column | neck_column.stl | 112 x 31 x 61 | 29.5 | PLA | 1509 |
| neck lid | neck_lid.stl | 26 x 26 x 10 | 2.9 | PLA | 5 |
| neck pitch rear hub | neck_pitch_rear_hub.stl | 31 x 32 x 9 | 3.9 | PLA | 0 (none) |
| head pitch rear hub | head_pitch_rear_hub.stl | 31 x 32 x 9 | 3.9 | PLA | 0 (none) |
| head roll rear hub | head_roll_rear_hub.stl | 28 x 27 x 10 | 2.7 | PLA | 0 (none) |
| head pitch lid | head_pitch_lid.stl | 26 x 26 x 11 | 2.7 | PLA | 4 |
| head fork | head_fork.stl | 63 x 56 x 40 | 15.6 | PLA | 751 |
| head yaw sheet | head_yaw_sheet.stl | 9 x 25 x 38 | 1.5 | PLA | 178 |
| head yaw bracket | head_yaw_bracket.stl | 25 x 38 x 26 | 8.6 | PLA | 517 |
| head roll lid | head_roll_lid.stl | 25 x 7 x 38 | 1.8 | PLA | 73 |
| head frame | head_frame.stl | 155 x 111 x 53 | 64.5 | PLA | 5237 |
| hood | hood.stl | 63 x 116 x 164 | 58.5 | PLA | 3392 |
| jaw | jaw.stl | 43 x 116 x 98 | 38.9 | PLA | 969 |
| jaw soft insert | jaw_soft_insert.stl | 30 x 111 x 5 | 16.3 | TPU 95A | 0 (none) |
| mouth roof | mouth_roof.stl | 43 x 111 x 3 | 15.0 | TPU 95A | 3 |
| face | face.stl | 55 x 109 x 3 | 10.2 | PLA | 54 |
| eye ring | eye_ring.stl | 37 x 38 x 12 | 9.9 | PLA | 0 (none) |
| eye iris | eye_iris.stl | 21 x 22 x 10 | 2.7 | PLA | 0 (none) |

The head frame prints in orange, in one filament: only its rim shows below the hood. The hood is modelled in two colours, a white top and an orange 5 mm band at its rim: one STL, so print it white and paint the band, or split the colour in a multi-material slicer.
A part with an overhang figure needs support or a bridge there; tools/printable.py counts faces, not a slicer, so it overstates short bridges. Check each in your slicer.


## Print one joint first

Before buying the rest, print `L_thigh_frame`, `L_knee_lid` and `L_shin`, with 1 MG996R, its 25T aluminium disc horn and its 4 M3 horn screws, 1 6704ZZ,
4 M3 x 16 and 2 M3 x 10 self-tapping through its ears. It tests: does the servo sit in its tray; does the bearing press into the seat and over the horn; do the screws bite;
how much the shin flexes with about 1.3 kg hung from it, off-centre as a foot would load it. Note what fits, and change the spec, not the STL.
