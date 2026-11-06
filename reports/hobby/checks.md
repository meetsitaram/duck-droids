# Physical checks

spec: `spec/robot.json`, 2026-11-06 11:26, 51 s

204 checks: 201 pass, 3 warn, **0 fail**

## targets

| status | item | detail |
|---|---|---|
| WARN | height | 0.373 m: 1.41 x microduck's 0.264 m (proportions are checked at this scale) |
| PASS | head_length_m | 0.164 (microduck 0.123 x 1.41 = 0.174 +/- 15 %) |
| PASS | head_width_m | 0.115 (microduck 0.092 x 1.41 = 0.130 +/- 15 %) |
| PASS | head_height_m | 0.074 (microduck 0.059 x 1.41 = 0.083 +/- 15 %) |
| PASS | head_bottom_z | 0.298 (microduck 0.205 x 1.41 = 0.289 +/- 15 %) |
| PASS | neck_pitch_z | 0.188 (microduck 0.139 x 1.41 = 0.196 +/- 15 %) |
| PASS | hip_pitch_z | 0.124 (microduck 0.089 x 1.41 = 0.126 +/- 15 %) |
| PASS | body_width_m | 0.080 (microduck 0.064 x 1.41 = 0.090 +/- 15 %) |
| PASS | overall_width_m | 0.187 (microduck 0.141 x 1.41 = 0.199 +/- 15 %) |
| PASS | foot_length_m | 0.069 (microduck 0.054 x 1.41 = 0.076 +/- 15 %) |

## mass

| status | item | detail |
|---|---|---|
| PASS | total | 1.941 kg bottom-up (budget 1.95 kg; microduck 0.8 kg) |

## printable

| status | item | detail |
|---|---|---|
| PASS | largest part | 331 printed parts; largest head: 164 mm, on a 256 mm bed |

## axis

| status | item | detail |
|---|---|---|
| PASS | L_hip_yaw | MG996R 0.0 mm off the axis |
| PASS | R_hip_yaw | MG996R 0.0 mm off the axis |
| PASS | L_hip_roll | MG996R 0.0 mm off the axis |
| PASS | R_hip_roll | MG996R 0.0 mm off the axis |
| PASS | L_hip_pitch | MG996R 0.0 mm off the axis |
| PASS | R_hip_pitch | MG996R 0.0 mm off the axis |
| PASS | L_knee | DS3218 0.0 mm off the axis |
| PASS | R_knee | DS3218 0.0 mm off the axis |
| PASS | L_ankle_pitch | MG996R 0.0 mm off the axis |
| PASS | R_ankle_pitch | MG996R 0.0 mm off the axis |
| PASS | neck_pitch | DS3218 0.0 mm off the axis |
| PASS | head_pitch | MG996R 0.0 mm off the axis |
| PASS | head_yaw | MG90S 0.0 mm off the axis |
| PASS | head_roll | MG90S 0.0 mm off the axis |
| PASS | beak | MG90S 0.0 mm off the axis |

## bearing

| status | item | detail |
|---|---|---|
| PASS | L hip yaw horn bearing outer race | 0.0 mm off the axis, on trunk |
| PASS | R hip yaw horn bearing outer race | 0.0 mm off the axis, on trunk |
| PASS | neck pitch rear bearing inner race | 0.0 mm off the axis, on trunk |
| PASS | L hip yaw horn bearing inner race | 0.0 mm off the axis, on L_hip_yaw_link |
| PASS | L hip roll horn bearing outer race | 0.0 mm off the axis, on L_hip_yaw_link |
| PASS | R hip yaw horn bearing inner race | 0.0 mm off the axis, on R_hip_yaw_link |
| PASS | R hip roll horn bearing outer race | 0.0 mm off the axis, on R_hip_yaw_link |
| PASS | L hip roll horn bearing inner race | 0.0 mm off the axis, on L_hip_roll_link |
| PASS | L hip pitch horn bearing inner race | 0.0 mm off the axis, on L_hip_roll_link |
| PASS | R hip roll horn bearing inner race | 0.0 mm off the axis, on R_hip_roll_link |
| PASS | R hip pitch horn bearing inner race | 0.0 mm off the axis, on R_hip_roll_link |
| PASS | L hip pitch horn bearing outer race | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | L knee horn bearing outer race | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | R hip pitch horn bearing outer race | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | R knee horn bearing outer race | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | L ankle bearing inner race | 0.0 mm off the axis, on L_knee_link |
| PASS | L knee horn bearing inner race | 0.0 mm off the axis, on L_knee_link |
| PASS | R ankle bearing inner race | 0.0 mm off the axis, on R_knee_link |
| PASS | R knee horn bearing inner race | 0.0 mm off the axis, on R_knee_link |
| PASS | L ankle bearing outer race | 0.0 mm off the axis, on L_foot |
| PASS | R ankle bearing outer race | 0.0 mm off the axis, on R_foot |
| PASS | neck pitch rear bearing outer race | 0.0 mm off the axis, on neck_link |
| PASS | head pitch rear bearing outer race | 0.0 mm off the axis, on neck_link |
| PASS | head pitch rear bearing inner race | 0.0 mm off the axis, on head_pitch_link |
| PASS | head yaw horn bearing outer race | 0.0 mm off the axis, on head_pitch_link |
| PASS | head yaw horn bearing inner race | 0.0 mm off the axis, on head_yaw_link |
| PASS | head roll horn bearing outer race | 0.0 mm off the axis, on head_yaw_link |
| PASS | head roll rear bearing outer race | 0.0 mm off the axis, on head_yaw_link |
| PASS | head roll horn bearing inner race | 0.0 mm off the axis, on head |
| PASS | head roll rear bearing inner race | 0.0 mm off the axis, on head |
| PASS | L hip yaw horn races | on ['trunk', 'L_hip_yaw_link'] |
| PASS | R hip yaw horn races | on ['trunk', 'R_hip_yaw_link'] |
| PASS | neck pitch rear races | on ['trunk', 'neck_link'] |
| PASS | L hip roll horn races | on ['L_hip_yaw_link', 'L_hip_roll_link'] |
| PASS | R hip roll horn races | on ['R_hip_yaw_link', 'R_hip_roll_link'] |
| PASS | L hip pitch horn races | on ['L_hip_roll_link', 'L_hip_pitch_link'] |
| PASS | R hip pitch horn races | on ['R_hip_roll_link', 'R_hip_pitch_link'] |
| PASS | L knee horn races | on ['L_hip_pitch_link', 'L_knee_link'] |
| PASS | R knee horn races | on ['R_hip_pitch_link', 'R_knee_link'] |
| PASS | L ankle races | on ['L_knee_link', 'L_foot'] |
| PASS | R ankle races | on ['R_knee_link', 'R_foot'] |
| PASS | head pitch rear races | on ['neck_link', 'head_pitch_link'] |
| PASS | head yaw horn races | on ['head_pitch_link', 'head_yaw_link'] |
| PASS | head roll horn races | on ['head_yaw_link', 'head'] |
| PASS | head roll rear races | on ['head_yaw_link', 'head'] |

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
| PASS | top plate | 0.00 % outside the skin |
| PASS | battery 2S 850 mAh | 0.30 % outside the skin |
| PASS | L 6 V BEC | 0.00 % outside the skin |
| PASS | R 6 V BEC | 0.00 % outside the skin |
| PASS | L regulator arm 0 | 0.00 % outside the skin |
| PASS | L regulator arm 1 | 0.00 % outside the skin |
| PASS | R regulator arm 0 | 0.00 % outside the skin |
| PASS | R regulator arm 1 | 0.00 % outside the skin |
| PASS | L regulator drop 0 | 0.00 % outside the skin |
| PASS | L regulator drop 1 | 0.00 % outside the skin |
| PASS | R regulator drop 0 | 0.00 % outside the skin |
| PASS | R regulator drop 1 | 0.00 % outside the skin |
| PASS | IMU | 0.00 % outside the skin |
| PASS | Pi Zero 2 W | 0.00 % outside the skin |
| PASS | Pi post 0 | 0.00 % outside the skin |
| PASS | Pi post 1 | 0.00 % outside the skin |
| PASS | Pi post 2 | 0.00 % outside the skin |
| PASS | Pi post 3 | 0.00 % outside the skin |
| PASS | PWM bonnet | 0.00 % outside the skin |
| PASS | PWM bonnet header | 0.00 % outside the skin |
| PASS | Pi 5 V converter | 0.00 % outside the skin |
| PASS | battery strap | 0.00 % outside the skin |
| PASS | pack hanger 0 | 0.00 % outside the skin |
| PASS | pack hanger 1 | 0.00 % outside the skin |
| PASS | body post 0 | 0.00 % outside the skin |
| PASS | body post 1 | 0.00 % outside the skin |
| PASS | head frame | 0.00 % outside the skin |
| PASS | head top plate wide | 0.00 % outside the skin |
| PASS | L head rail | 0.00 % outside the skin |
| PASS | R head rail | 0.00 % outside the skin |
| PASS | R head hinge boss | 0.00 % outside the skin |
| PASS | Pi mount | 0.00 % outside the skin |
| PASS | Pi mount 2 | 0.00 % outside the skin |
| PASS | Pi plate | 0.00 % outside the skin |
| PASS | camera | 0.00 % outside the skin |
| PASS | L base riser top | 0.00 % outside the skin |
| PASS | Pi base tab | 0.00 % outside the skin |

## sweep

| status | item | detail |
|---|---|---|
| PASS | L_hip_yaw | [-0.45, +0.45] rad clear |
| PASS | L_hip_roll | [-0.33, +0.33] rad clear |
| PASS | L_hip_pitch | [-1.30, +0.43] rad clear |
| PASS | L_knee | [-1.10, +1.05] rad clear |
| PASS | L_ankle_pitch | [-1.30, +1.30] rad clear |
| PASS | neck_pitch | [-0.15, +1.60] rad clear |
| WARN | head_pitch | [-1.60, +1.60] rad clear; lower: head / trunk: lower shell / body at -1.13 rad (pose-dependent) |
| PASS | head_yaw | [-2.50, +2.50] rad clear |
| PASS | head_roll | [-0.25, +0.25] rad clear |
| PASS | beak | [+0.00, +0.40] rad clear |

## poses

| status | item | detail |
|---|---|---|
| PASS | stand (microduck stance): balance | CoM 2.3 cm inside the feet |
| PASS | stand (microduck stance): within limits | yes |
| PASS | stand (microduck stance): collisions | none |
| PASS | crouch: balance | CoM 2.3 cm inside the feet |
| PASS | crouch: within limits | yes |
| PASS | crouch: collisions | none |
| PASS | deep squat: balance | CoM 2.3 cm inside the feet |
| PASS | deep squat: within limits | yes |
| PASS | deep squat: collisions | none |
| WARN | single-leg stance (walking): balance | CoM 3.7 cm outside the stance foot: a dynamic gait, no static single-leg balance (no ankle roll) |
| PASS | single-leg stance (walking): within limits | yes |
| PASS | single-leg stance (walking): collisions | none |
| PASS | floor pick: balance | CoM 2.3 cm inside the feet |
| PASS | floor pick: within limits | yes |
| PASS | floor pick: collisions | none |
| PASS | head tucked in: balance | CoM 2.3 cm inside the feet |
| PASS | head tucked in: within limits | yes |
| PASS | head tucked in: collisions | none |
| PASS | head forward and down, beak open: balance | CoM 2.3 cm inside the feet |
| PASS | head forward and down, beak open: within limits | yes |
| PASS | head forward and down, beak open: collisions | none |

## torque

| status | item | detail |
|---|---|---|
| PASS | L_hip_roll | 0.49 N m x 1.5 in 'single-leg stance (walking)' vs peak 1.08 N m (1 x MG996R): 68 % used |
| PASS | R_knee | 0.41 N m in 'crouch' vs rated 0.67 N m (1 x DS3218): 62 % used |
| PASS | L_knee | 0.41 N m in 'crouch' vs rated 0.67 N m (1 x DS3218): 62 % used |
| PASS | head_pitch | 0.19 N m in 'head forward and down, beak open' vs rated 0.36 N m (1 x MG996R): 52 % used |
| PASS | neck_pitch | 0.33 N m in 'head forward and down, beak open' vs rated 0.67 N m (1 x DS3218): 49 % used |
| PASS | L_hip_pitch | 0.29 N m x 1.5 in 'floor pick' vs peak 1.08 N m (1 x MG996R): 41 % used |
| PASS | R_hip_pitch | 0.29 N m x 1.5 in 'floor pick' vs peak 1.08 N m (1 x MG996R): 41 % used |
| PASS | R_hip_roll | 0.12 N m in 'crouch' vs rated 0.36 N m (1 x MG996R): 35 % used |
| PASS | beak | 0.02 N m in 'head tucked in' vs rated 0.07 N m (1 x MG90S): 28 % used |
| PASS | L_ankle_pitch | 0.18 N m x 1.5 in 'single-leg stance (walking)' vs peak 1.08 N m (1 x MG996R): 25 % used |
| PASS | R_ankle_pitch | 0.09 N m in 'head forward and down, beak open' vs rated 0.36 N m (1 x MG996R): 25 % used |
| PASS | L_hip_yaw | 0.16 N m x 1.5 in 'single-leg stance (walking)' vs peak 1.08 N m (1 x MG996R): 22 % used |
| PASS | R_hip_yaw | 0.06 N m in 'head forward and down, beak open' vs rated 0.36 N m (1 x MG996R): 17 % used |
| PASS | head_roll | 0.00 N m in 'crouch' vs rated 0.07 N m (1 x MG90S): 5 % used |
| PASS | head_yaw | 0.00 N m in 'head forward and down, beak open' vs rated 0.07 N m (1 x MG90S): 1 % used |
