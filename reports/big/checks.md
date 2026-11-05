# Physical checks

spec: `spec/robot.json`, 2026-11-05 15:22, 163 s

151 checks: 146 pass, 5 warn, **0 fail**

## targets

| status | item | detail |
|---|---|---|
| WARN | height | 1.797 m: 6.81 x microduck's 0.264 m (proportions are checked at this scale) |
| PASS | head_length_m | 0.878 (microduck 0.123 x 6.81 = 0.837 +/- 25 %) |
| PASS | head_width_m | 0.638 (microduck 0.092 x 6.81 = 0.626 +/- 25 %) |
| PASS | head_height_m | 0.444 (microduck 0.059 x 6.81 = 0.402 +/- 25 %) |
| PASS | head_bottom_z | 1.353 (microduck 0.205 x 6.81 = 1.396 +/- 25 %) |
| PASS | neck_pitch_z | 0.940 (microduck 0.139 x 6.81 = 0.946 +/- 25 %) |
| PASS | hip_pitch_z | 0.674 (microduck 0.089 x 6.81 = 0.606 +/- 25 %) |
| PASS | body_width_m | 0.410 (microduck 0.064 x 6.81 = 0.436 +/- 25 %) |
| PASS | overall_width_m | 0.740 (microduck 0.141 x 6.81 = 0.960 +/- 25 %) |
| PASS | foot_length_m | 0.330 (microduck 0.054 x 6.81 = 0.368 +/- 25 %) |

## mass

| status | item | detail |
|---|---|---|
| PASS | total | 98.585 kg bottom-up (budget 115.0 kg; microduck 0.8 kg) |

## printable

| status | item | detail |
|---|---|---|
| PASS | largest part | 68 printed parts; largest hood panel 0c: 240 mm, on a 256 mm bed |

## axis

| status | item | detail |
|---|---|---|
| PASS | L_hip_yaw | RS04 0.0 mm off the axis |
| PASS | R_hip_yaw | RS04 0.0 mm off the axis |
| PASS | L_hip_roll | RS04 0.0 mm off the axis |
| PASS | R_hip_roll | RS04 0.0 mm off the axis |
| PASS | L_hip_pitch | RS04 0.0 mm off the axis |
| PASS | R_hip_pitch | RS04 0.0 mm off the axis |
| PASS | L_ankle_pitch | RS04 0.0 mm off the axis |
| PASS | R_ankle_pitch | RS04 0.0 mm off the axis |
| PASS | neck_pitch | RS04 0.0 mm off the axis |
| PASS | head_yaw | RS03 0.0 mm off the axis |
| PASS | head_roll | RS03 0.0 mm off the axis |

## bearing

| status | item | detail |
|---|---|---|
| PASS | L hip yaw bearing outer race | 0.0 mm off the axis, on trunk |
| PASS | R hip yaw bearing outer race | 0.0 mm off the axis, on trunk |
| PASS | L hip yaw bearing inner race | 0.0 mm off the axis, on L_hip_yaw_link |
| PASS | R hip yaw bearing inner race | 0.0 mm off the axis, on R_hip_yaw_link |
| PASS | L knee bearing outer race | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | L knee far bearing outer race | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | R knee bearing outer race | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | R knee far bearing outer race | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | L knee bearing inner race | 0.0 mm off the axis, on L_knee_link |
| PASS | L knee far bearing inner race | 0.0 mm off the axis, on L_knee_link |
| PASS | L ankle bearing inner race | 0.0 mm off the axis, on L_knee_link |
| PASS | R knee bearing inner race | 0.0 mm off the axis, on R_knee_link |
| PASS | R knee far bearing inner race | 0.0 mm off the axis, on R_knee_link |
| PASS | R ankle bearing inner race | 0.0 mm off the axis, on R_knee_link |
| PASS | L ankle bearing outer race | 0.0 mm off the axis, on L_foot |
| PASS | R ankle bearing outer race | 0.0 mm off the axis, on R_foot |
| PASS | head pitch L bearing outer race | 0.0 mm off the axis, on neck_link |
| PASS | head pitch R bearing outer race | 0.0 mm off the axis, on neck_link |
| PASS | head pitch L bearing inner race | 0.0 mm off the axis, on head_pitch_link |
| PASS | head pitch R bearing inner race | 0.0 mm off the axis, on head_pitch_link |
| PASS | L hip yaw races | on ['trunk', 'L_hip_yaw_link'] |
| PASS | R hip yaw races | on ['trunk', 'R_hip_yaw_link'] |
| PASS | L knee races | on ['L_hip_pitch_link', 'L_knee_link'] |
| PASS | L knee far races | on ['L_hip_pitch_link', 'L_knee_link'] |
| PASS | R knee races | on ['R_hip_pitch_link', 'R_knee_link'] |
| PASS | R knee far races | on ['R_hip_pitch_link', 'R_knee_link'] |
| PASS | L ankle races | on ['L_knee_link', 'L_foot'] |
| PASS | R ankle races | on ['R_knee_link', 'R_foot'] |
| PASS | head pitch L races | on ['neck_link', 'head_pitch_link'] |
| PASS | head pitch R races | on ['neck_link', 'head_pitch_link'] |

## static

| status | item | detail |
|---|---|---|
| PASS | zero pose | 0 overlaps |

## covers

| status | item | detail |
|---|---|---|
| PASS | motors clear of the covers | 0 cover / motor crossings |

## connect

| status | item | detail |
|---|---|---|
| PASS | trunk structure |  |
| PASS | trunk covers mounted |  |
| PASS | L_hip_yaw_link structure |  |
| PASS | L_hip_yaw_link covers mounted |  |
| PASS | R_hip_yaw_link structure |  |
| PASS | R_hip_yaw_link covers mounted |  |
| PASS | L_hip_roll_link structure |  |
| PASS | L_hip_roll_link covers mounted |  |
| PASS | R_hip_roll_link structure |  |
| PASS | R_hip_roll_link covers mounted |  |
| PASS | L_hip_pitch_link structure |  |
| PASS | L_hip_pitch_link covers mounted |  |
| PASS | R_hip_pitch_link structure |  |
| PASS | R_hip_pitch_link covers mounted |  |
| PASS | L_knee_link structure |  |
| PASS | L_knee_link covers mounted |  |
| PASS | R_knee_link structure |  |
| PASS | R_knee_link covers mounted |  |
| PASS | L_foot structure |  |
| PASS | L_foot covers mounted |  |
| PASS | R_foot structure |  |
| PASS | R_foot covers mounted |  |
| PASS | neck_link structure |  |
| PASS | neck_link covers mounted |  |
| PASS | head_pitch_link structure |  |
| PASS | head_pitch_link covers mounted |  |
| PASS | head_yaw_link structure |  |
| PASS | head_yaw_link covers mounted |  |
| PASS | head structure |  |
| PASS | head covers mounted |  |
| PASS | beak_link structure |  |
| PASS | beak_link covers mounted |  |
| PASS | L_hip_yaw axis |  |
| PASS | R_hip_yaw axis |  |
| PASS | L_hip_roll axis |  |
| PASS | R_hip_roll axis |  |
| PASS | L_hip_pitch axis |  |
| PASS | R_hip_pitch axis |  |
| PASS | L_knee axis |  |
| PASS | R_knee axis |  |
| PASS | L_ankle_pitch axis |  |
| PASS | R_ankle_pitch axis |  |
| PASS | neck_pitch axis |  |
| PASS | head_pitch axis |  |
| PASS | head_yaw axis |  |
| PASS | head_roll axis |  |
| PASS | beak axis |  |

## skin

| status | item | detail |
|---|---|---|
| PASS | battery 13S | 0.00 % outside the skin |
| PASS | battery BMS, fuse and case, allowance | 0.00 % outside the skin |
| PASS | computer and power boards | 0.00 % outside the skin |

## sweep

| status | item | detail |
|---|---|---|
| PASS | L_hip_yaw | [-0.45, +0.45] rad clear |
| PASS | L_hip_roll | [-0.33, +0.33] rad clear |
| PASS | L_hip_pitch | [-1.57, +0.43] rad clear |
| PASS | L_knee | [-0.92, +0.30] rad clear |
| PASS | L_ankle_pitch | [-1.20, +1.20] rad clear |
| PASS | neck_pitch | [-0.15, +1.60] rad clear |
| WARN | head_pitch | [-1.60, +1.60] rad clear; lower: head / trunk: hood panel 0Rl / body panel MR at -1.60 rad (pose-dependent); upper: beak_link / trunk: beak panel 1 / neck plate L at +1.60 rad (pose-dependent) |
| PASS | head_yaw | [-2.50, +2.50] rad clear |
| PASS | head_roll | [-0.38, +0.38] rad clear |
| PASS | beak | [+0.00, +0.40] rad clear |

## poses

| status | item | detail |
|---|---|---|
| PASS | stand (microduck stance): balance | CoM 14.9 cm inside the feet |
| PASS | stand (microduck stance): within limits | yes |
| PASS | stand (microduck stance): collisions | none |
| PASS | crouch: balance | CoM 14.8 cm inside the feet |
| PASS | crouch: within limits | yes |
| PASS | crouch: collisions | none |
| PASS | deep squat: balance | CoM 14.9 cm inside the feet |
| WARN | deep squat: within limits | L_knee -1.08 outside [-0.92, +0.30]; R_knee -1.08 outside [-0.92, +0.30] |
| PASS | deep squat: collisions | none |
| WARN | single-leg stance (walking): balance | CoM 18.4 cm outside the stance foot: a dynamic gait, no static single-leg balance (no ankle roll) |
| PASS | single-leg stance (walking): within limits | yes |
| PASS | single-leg stance (walking): collisions | none |
| PASS | floor pick: balance | CoM 14.8 cm inside the feet |
| WARN | floor pick: within limits | L_knee -1.08 outside [-0.92, +0.30]; R_knee -1.08 outside [-0.92, +0.30] |
| PASS | floor pick: collisions | none |
| PASS | head tucked in: balance | CoM 14.9 cm inside the feet |
| PASS | head tucked in: within limits | yes |
| PASS | head tucked in: collisions | none |
| PASS | head forward and down, beak open: balance | CoM 14.8 cm inside the feet |
| PASS | head forward and down, beak open: within limits | yes |
| PASS | head forward and down, beak open: collisions | none |

## torque

| status | item | detail |
|---|---|---|
| PASS | L_knee | 106.82 N m in 'crouch' vs rated 123.20 N m (2 x RS04 x 1.5): 87 % used |
| PASS | R_knee | 106.82 N m in 'crouch' vs rated 123.20 N m (2 x RS04 x 1.5): 87 % used |
| PASS | L_hip_roll | 129.68 N m x 1.5 in 'single-leg stance (walking)' vs peak 240.00 N m (2 x RS04): 81 % used |
| PASS | beak | 3.01 N m in 'stand (microduck stance)' vs rated 5.00 N m (1 x RS00): 60 % used |
| PASS | L_ankle_pitch | 47.68 N m x 1.5 in 'single-leg stance (walking)' vs peak 120.00 N m (1 x RS04): 60 % used |
| PASS | R_ankle_pitch | 23.70 N m in 'crouch' vs rated 40.00 N m (1 x RS04): 59 % used |
| PASS | L_hip_yaw | 45.78 N m x 1.5 in 'single-leg stance (walking)' vs peak 120.00 N m (1 x RS04): 57 % used |
| PASS | R_hip_roll | 38.74 N m in 'crouch' vs rated 80.00 N m (2 x RS04): 48 % used |
| PASS | neck_pitch | 75.60 N m in 'head tucked in' vs rated 240.00 N m (2 x RS04): 47 % used |
| PASS | head_pitch | 31.84 N m in 'crouch' vs rated 76.92 N m (1 x RS04 x 1.9): 41 % used |
| PASS | R_hip_yaw | 10.80 N m in 'stand (microduck stance)' vs rated 40.00 N m (1 x RS04): 27 % used |
| PASS | L_hip_pitch | 16.44 N m in 'crouch' vs rated 80.00 N m (2 x RS04): 21 % used |
| PASS | R_hip_pitch | 16.44 N m in 'crouch' vs rated 80.00 N m (2 x RS04): 21 % used |
| PASS | head_roll | 0.00 N m in 'crouch' vs rated 20.00 N m (1 x RS03): 0 % used |
| PASS | head_yaw | 0.00 N m in 'head forward and down, beak open' vs rated 60.00 N m (1 x RS03): 0 % used |
