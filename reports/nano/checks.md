# Physical checks

spec: `spec/robot.json`, 2026-11-06 11:23, 23 s

176 checks: 171 pass, 5 warn, **0 fail**

## targets

| status | item | detail |
|---|---|---|
| WARN | height | 0.206 m: 0.78 x microduck's 0.264 m (proportions are checked at this scale) |
| PASS | head_length_m | 0.088 (microduck 0.123 x 0.78 = 0.096 +/- 35 %) |
| PASS | head_width_m | 0.076 (microduck 0.092 x 0.78 = 0.072 +/- 35 %) |
| PASS | head_height_m | 0.052 (microduck 0.059 x 0.78 = 0.046 +/- 35 %) |
| PASS | head_bottom_z | 0.153 (microduck 0.205 x 0.78 = 0.160 +/- 35 %) |
| PASS | neck_pitch_z | 0.134 (microduck 0.139 x 0.78 = 0.108 +/- 35 %) |
| PASS | hip_pitch_z | 0.074 (microduck 0.089 x 0.78 = 0.069 +/- 35 %) |
| PASS | body_width_m | 0.061 (microduck 0.064 x 0.78 = 0.050 +/- 35 %) |
| PASS | overall_width_m | 0.086 (microduck 0.141 x 0.78 = 0.110 +/- 35 %) |
| PASS | foot_length_m | 0.054 (microduck 0.054 x 0.78 = 0.042 +/- 35 %) |

## mass

| status | item | detail |
|---|---|---|
| PASS | total | 0.370 kg bottom-up (budget 0.38 kg; microduck 0.8 kg) |

## printable

| status | item | detail |
|---|---|---|
| PASS | largest part | 224 printed parts; largest body: 101 mm, on a 256 mm bed |

## axis

| status | item | detail |
|---|---|---|
| PASS | L_ankle_pitch | SG90 0.0 mm off the axis |
| PASS | R_ankle_pitch | SG90 0.0 mm off the axis |
| PASS | L_knee | MG90S_5V 0.0 mm off the axis |
| PASS | R_knee | MG90S_5V 0.0 mm off the axis |
| PASS | L_hip_pitch | SG90 0.0 mm off the axis |
| PASS | R_hip_pitch | SG90 0.0 mm off the axis |
| PASS | L_hip_roll | MG90S_5V 0.0 mm off the axis |
| PASS | R_hip_roll | MG90S_5V 0.0 mm off the axis |
| PASS | L_hip_yaw | SG90 0.0 mm off the axis |
| PASS | R_hip_yaw | SG90 0.0 mm off the axis |
| PASS | neck_pitch | SG90 0.0 mm off the axis |
| PASS | head_pitch | SG90 0.0 mm off the axis |
| PASS | beak | SG90 0.0 mm off the axis |

## bearing

| status | item | detail |
|---|---|---|
| PASS | L ankle pitch rear bearing stub | 0.0 mm off the axis, on L_knee_link |
| PASS | L knee rear bearing bushing | 0.0 mm off the axis, on L_knee_link |
| PASS | R ankle pitch rear bearing stub | 0.0 mm off the axis, on R_knee_link |
| PASS | R knee rear bearing bushing | 0.0 mm off the axis, on R_knee_link |
| PASS | L ankle pitch rear bearing bushing | 0.0 mm off the axis, on L_foot |
| PASS | R ankle pitch rear bearing bushing | 0.0 mm off the axis, on R_foot |
| PASS | L knee rear bearing stub | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | L hip pitch rear bearing stub | 0.0 mm off the axis, on L_hip_pitch_link |
| PASS | R knee rear bearing stub | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | R hip pitch rear bearing stub | 0.0 mm off the axis, on R_hip_pitch_link |
| PASS | L hip pitch rear bearing bushing | 0.0 mm off the axis, on L_hip_roll_link |
| PASS | L hip roll rear bearing bushing | 0.0 mm off the axis, on L_hip_roll_link |
| PASS | R hip pitch rear bearing bushing | 0.0 mm off the axis, on R_hip_roll_link |
| PASS | R hip roll rear bearing bushing | 0.0 mm off the axis, on R_hip_roll_link |
| PASS | L hip roll rear bearing stub | 0.0 mm off the axis, on L_hip_yaw_link |
| PASS | L hip yaw rear bearing bushing | 0.0 mm off the axis, on L_hip_yaw_link |
| PASS | R hip roll rear bearing stub | 0.0 mm off the axis, on R_hip_yaw_link |
| PASS | R hip yaw rear bearing bushing | 0.0 mm off the axis, on R_hip_yaw_link |
| PASS | L hip yaw rear bearing stub | 0.0 mm off the axis, on trunk |
| PASS | R hip yaw rear bearing stub | 0.0 mm off the axis, on trunk |
| PASS | L ankle pitch rear races | on ['L_knee_link', 'L_foot'] |
| PASS | L knee rear races | on ['L_knee_link', 'L_hip_pitch_link'] |
| PASS | R ankle pitch rear races | on ['R_knee_link', 'R_foot'] |
| PASS | R knee rear races | on ['R_knee_link', 'R_hip_pitch_link'] |
| PASS | L hip pitch rear races | on ['L_hip_pitch_link', 'L_hip_roll_link'] |
| PASS | R hip pitch rear races | on ['R_hip_pitch_link', 'R_hip_roll_link'] |
| PASS | L hip roll rear races | on ['L_hip_roll_link', 'L_hip_yaw_link'] |
| PASS | R hip roll rear races | on ['R_hip_roll_link', 'R_hip_yaw_link'] |
| PASS | L hip yaw rear races | on ['L_hip_yaw_link', 'trunk'] |
| PASS | R hip yaw rear races | on ['R_hip_yaw_link', 'trunk'] |

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
| PASS | L_knee_link structure |  |
| PASS | L_knee_link covers mounted |  |
| PASS | R_knee_link structure |  |
| PASS | R_knee_link covers mounted |  |
| PASS | L_foot structure |  |
| PASS | L_foot covers mounted |  |
| PASS | R_foot structure |  |
| PASS | R_foot covers mounted |  |
| PASS | L_hip_pitch_link structure |  |
| PASS | L_hip_pitch_link covers mounted |  |
| PASS | R_hip_pitch_link structure |  |
| PASS | R_hip_pitch_link covers mounted |  |
| PASS | L_hip_roll_link structure |  |
| PASS | L_hip_roll_link covers mounted |  |
| PASS | R_hip_roll_link structure |  |
| PASS | R_hip_roll_link covers mounted |  |
| PASS | L_hip_yaw_link structure |  |
| PASS | L_hip_yaw_link covers mounted |  |
| PASS | R_hip_yaw_link structure |  |
| PASS | R_hip_yaw_link covers mounted |  |
| PASS | trunk structure |  |
| PASS | trunk covers mounted |  |
| PASS | neck_link structure |  |
| PASS | neck_link covers mounted |  |
| PASS | head structure |  |
| PASS | head covers mounted |  |
| PASS | beak_link structure |  |
| PASS | beak_link covers mounted |  |
| PASS | L_ankle_pitch axis |  |
| PASS | R_ankle_pitch axis |  |
| PASS | L_knee axis |  |
| PASS | R_knee axis |  |
| PASS | L_hip_pitch axis |  |
| PASS | R_hip_pitch axis |  |
| PASS | L_hip_roll axis |  |
| PASS | R_hip_roll axis |  |
| PASS | L_hip_yaw axis |  |
| PASS | R_hip_yaw axis |  |
| PASS | neck_pitch axis |  |
| PASS | head_pitch axis |  |
| PASS | beak axis |  |

## skin

| status | item | detail |
|---|---|---|
| PASS | L hip yaw cradle floor | 0.00 % outside the skin |
| PASS | L hip yaw cradle wall | 0.00 % outside the skin |
| PASS | L hip yaw cradle near block | 0.00 % outside the skin |
| PASS | L hip yaw cradle far block | 0.00 % outside the skin |
| PASS | L hip yaw cradle corner 0 | 0.00 % outside the skin |
| PASS | L hip yaw cradle corner 1 | 0.00 % outside the skin |
| PASS | L hip yaw ear clamp near | 0.00 % outside the skin |
| PASS | L hip yaw ear clamp far | 0.00 % outside the skin |
| PASS | L hip yaw ear clamp strip | 0.00 % outside the skin |
| PASS | L hip yaw rear bearing stub | 0.00 % outside the skin |
| PASS | L chassis bridge | 0.00 % outside the skin |
| PASS | chassis spine | 0.00 % outside the skin |
| PASS | Pi plate | 0.00 % outside the skin |
| PASS | battery tray | 0.00 % outside the skin |
| PASS | battery tray back | 0.00 % outside the skin |
| PASS | battery tray front | 0.00 % outside the skin |
| PASS | regulator shelf | 0.00 % outside the skin |
| PASS | Pi Zero 2 W | 0.00 % outside the skin |
| PASS | battery 2S 300 mAh | 0.00 % outside the skin |
| PASS | L 5 V regulator | 0.00 % outside the skin |
| PASS | servo header board | 0.00 % outside the skin |
| PASS | IMU | 0.00 % outside the skin |
| PASS | body boss 0 | 0.00 % outside the skin |
| PASS | body boss 1 | 0.00 % outside the skin |
| PASS | R hip yaw cradle floor | 0.00 % outside the skin |
| PASS | R hip yaw cradle wall | 0.00 % outside the skin |
| PASS | R hip yaw cradle near block | 0.00 % outside the skin |
| PASS | R hip yaw cradle far block | 0.00 % outside the skin |
| PASS | R hip yaw cradle corner 0 | 0.00 % outside the skin |
| PASS | R hip yaw cradle corner 1 | 0.00 % outside the skin |
| PASS | R hip yaw ear clamp near | 0.00 % outside the skin |
| PASS | R hip yaw ear clamp far | 0.00 % outside the skin |
| PASS | R hip yaw ear clamp strip | 0.00 % outside the skin |
| PASS | R hip yaw rear bearing stub | 0.00 % outside the skin |
| PASS | R chassis bridge | 0.00 % outside the skin |
| PASS | R 5 V regulator | 0.00 % outside the skin |

## sweep

| status | item | detail |
|---|---|---|
| PASS | L_ankle_pitch | [-0.50, +1.45] rad clear |
| PASS | L_knee | [-1.20, +0.20] rad clear |
| PASS | L_hip_pitch | [-0.70, +0.50] rad clear |
| WARN | L_hip_roll | [-0.35, +0.35] rad clear; lower: L_foot / R_foot: L ankle pitch bushing lip / R ankle pitch bushing lip at -0.07 rad (pose-dependent) |
| WARN | L_hip_yaw | [-0.40, +0.40] rad clear; upper: L_foot / R_foot: L ankle pitch bushing lip / R ankle pitch bushing lip at +0.18 rad (pose-dependent) |
| PASS | neck_pitch | [-0.20, +1.60] rad clear |
| PASS | head_pitch | [-1.30, +0.80] rad clear |
| PASS | beak | [+0.00, +0.45] rad clear |

## poses

| status | item | detail |
|---|---|---|
| PASS | stand (microduck stance): balance | CoM 2.5 cm inside the feet |
| PASS | stand (microduck stance): within limits | yes |
| PASS | stand (microduck stance): collisions | none |
| PASS | crouch: balance | CoM 2.5 cm inside the feet |
| PASS | crouch: within limits | yes |
| PASS | crouch: collisions | none |
| PASS | deep squat: balance | CoM 2.6 cm inside the feet |
| PASS | deep squat: within limits | yes |
| PASS | deep squat: collisions | none |
| WARN | single-leg stance (walking): balance | CoM 0.7 cm outside the stance foot: a dynamic gait, no static single-leg balance (no ankle roll) |
| PASS | single-leg stance (walking): within limits | yes |
| PASS | single-leg stance (walking): collisions | none |
| PASS | floor pick: balance | CoM 2.5 cm inside the feet |
| PASS | floor pick: within limits | yes |
| PASS | floor pick: collisions | none |
| PASS | head tucked in: balance | CoM 2.5 cm inside the feet |
| WARN | head tucked in: within limits | head_pitch -1.45 outside [-1.30, +0.80] |
| PASS | head tucked in: collisions | none |
| PASS | head forward and down, beak open: balance | CoM 2.5 cm inside the feet |
| PASS | head forward and down, beak open: within limits | yes |
| PASS | head forward and down, beak open: collisions | none |

## torque

| status | item | detail |
|---|---|---|
| PASS | L_knee | 0.08 N m x 1.5 in 'single-leg stance (walking)' vs peak 0.18 N m (1 x MG90S_5V): 71 % used |
| PASS | R_knee | 0.06 N m in 'crouch' vs rated 0.09 N m (1 x MG90S_5V): 65 % used |
| PASS | L_ankle_pitch | 0.05 N m x 1.5 in 'single-leg stance (walking)' vs peak 0.16 N m (1 x SG90): 50 % used |
| PASS | L_hip_roll | 0.05 N m x 1.5 in 'single-leg stance (walking)' vs peak 0.18 N m (1 x MG90S_5V): 45 % used |
| PASS | R_hip_roll | 0.03 N m in 'crouch' vs rated 0.09 N m (1 x MG90S_5V): 39 % used |
| PASS | L_hip_pitch | 0.04 N m x 1.5 in 'floor pick' vs peak 0.16 N m (1 x SG90): 34 % used |
| PASS | R_hip_pitch | 0.04 N m x 1.5 in 'floor pick' vs peak 0.16 N m (1 x SG90): 34 % used |
| PASS | R_ankle_pitch | 0.03 N m in 'stand (microduck stance)' vs rated 0.08 N m (1 x SG90): 33 % used |
| PASS | neck_pitch | 0.02 N m in 'head forward and down, beak open' vs rated 0.08 N m (1 x SG90): 32 % used |
| PASS | head_pitch | 0.01 N m in 'crouch' vs rated 0.08 N m (1 x SG90): 17 % used |
| PASS | L_hip_yaw | 0.01 N m x 1.5 in 'single-leg stance (walking)' vs peak 0.16 N m (1 x SG90): 14 % used |
| PASS | R_hip_yaw | 0.01 N m x 1.5 in 'floor pick' vs peak 0.16 N m (1 x SG90): 9 % used |
| PASS | beak | 0.00 N m in 'stand (microduck stance)' vs rated 0.08 N m (1 x SG90): 1 % used |
