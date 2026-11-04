# Physical checks

From tools/beak_linkage.py

49 checks: 48 pass, 1 warn, **0 fail**

## DRIVE

| status | item | detail |
|---|---|---|
| PASS | L_hip_yaw |  |
| PASS | R_hip_yaw |  |
| PASS | L_hip_roll |  |
| PASS | R_hip_roll |  |
| PASS | L_hip_pitch |  |
| PASS | R_hip_pitch |  |
| PASS | L_knee |  |
| PASS | R_knee |  |
| PASS | L_ankle_pitch |  |
| PASS | R_ankle_pitch |  |
| PASS | neck_pitch |  |
| PASS | head_pitch |  |
| PASS | head_yaw |  |
| PASS | head_roll |  |
| PASS | beak | a crank and a rod |

## SOLVE

| status | item | detail |
|---|---|---|
| PASS | jaw +0.00 rad |  |
| PASS | jaw +0.05 rad |  |
| PASS | jaw +0.10 rad |  |
| PASS | jaw +0.15 rad |  |
| PASS | jaw +0.20 rad |  |
| PASS | jaw +0.25 rad |  |
| PASS | jaw +0.30 rad |  |
| PASS | jaw +0.35 rad |  |
| PASS | jaw +0.40 rad |  |
| PASS | servo travel | 36 deg of crank for 23 deg of jaw |

## ANGLE

| status | item | detail |
|---|---|---|
| PASS | jaw +0.00 rad | 47 deg at the crank, 79 at the lever |
| PASS | jaw +0.05 rad | 53 deg at the crank, 82 at the lever |
| PASS | jaw +0.10 rad | 59 deg at the crank, 86 at the lever |
| PASS | jaw +0.15 rad | 64 deg at the crank, 90 at the lever |
| PASS | jaw +0.20 rad | 69 deg at the crank, 87 at the lever |
| PASS | jaw +0.25 rad | 74 deg at the crank, 83 at the lever |
| PASS | jaw +0.30 rad | 79 deg at the crank, 80 at the lever |
| PASS | jaw +0.35 rad | 83 deg at the crank, 77 at the lever |
| PASS | jaw +0.40 rad | 88 deg at the crank, 73 at the lever |

## CLEAR

| status | item | detail |
|---|---|---|
| PASS | beak crank / head | 0.000 cm3 at the worst pose |
| PASS | beak crank / beak_link | 0.000 cm3 at the worst pose |
| PASS | beak crank / head_yaw_link | 0.000 cm3 at the worst pose |
| PASS | beak crank / yaw servo, head rolled and yawed together | 0.000 cm3: keep |roll| under 0.1 rad when |yaw| is over 0.5 rad |
| PASS | beak crank / head_pitch_link | 0.000 cm3 at the worst pose |
| PASS | beak crank pin / head | 0.000 cm3 at the worst pose |
| PASS | beak crank pin / beak_link | 0.000 cm3 at the worst pose |
| PASS | beak crank pin / head_yaw_link | 0.000 cm3 at the worst pose |
| PASS | beak crank pin / yaw servo, head rolled and yawed together | 0.000 cm3: keep |roll| under 0.1 rad when |yaw| is over 0.5 rad |
| PASS | beak crank pin / head_pitch_link | 0.000 cm3 at the worst pose |
| PASS | beak rod / head | 0.006 cm3 at the worst pose |
| PASS | beak rod / beak_link | 0.000 cm3 at the worst pose |
| PASS | beak rod / head_yaw_link | 0.000 cm3 at the worst pose |
| WARN | beak rod / yaw servo, head rolled and yawed together | 0.207 cm3: keep |roll| under 0.1 rad when |yaw| is over 0.5 rad |
| PASS | beak rod / head_pitch_link | 0.000 cm3 at the worst pose |
