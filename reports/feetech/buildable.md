# Physical checks

From tools/buildable.py. LOAD is a beam estimate, not FEA: test prints decide.

84 checks: 80 pass, 0 warn, **4 fail**

## LOAD

| status | item | detail |
|---|---|---|
| FAIL | shin, under the knee horn | 15.3 MPa (allowed 15): 55 N, section 180 mm2 |
| PASS | shin, at the cap | 0.5 MPa (allowed 15): 55 N, section 1255 mm2 |
| PASS | thigh, hip to knee | 0.5 MPa (allowed 15): 55 N, section 808 mm2 |
| PASS | roll bracket, side arm | 14.9 MPa (allowed 15): 55 N, section 90 mm2 |
| PASS | roll bracket, front plate | 13.5 MPa (allowed 15): 55 N, section 60 mm2 |
| PASS | yaw bracket | 1.5 MPa (allowed 15): 55 N, section 920 mm2 |

## ONE

| status | item | detail |
|---|---|---|
| PASS | L hip yaw lid |  |
| PASS | L yaw bracket |  |
| PASS | L hip roll lid |  |
| PASS | L roll bracket |  |
| PASS | L thigh frame |  |
| PASS | L hip pitch lid |  |
| PASS | L knee lid |  |
| PASS | L shin |  |
| PASS | L shoe |  |
| PASS | L sole |  |
| PASS | L inner ear |  |
| PASS | chassis |  |
| PASS | neck column |  |
| PASS | neck lid |  |
| PASS | head pitch lid |  |
| PASS | head fork |  |
| PASS | head yaw bracket |  |
| PASS | head roll lid |  |
| PASS | head roll spacer |  |
| PASS | head roll rear spacer |  |
| PASS | head frame |  |
| PASS | jaw |  |
| PASS | jaw soft insert |  |
| PASS | face |  |
| PASS | eye ring |  |
| PASS | eye iris |  |

## WALL

| status | item | detail |
|---|---|---|
| PASS | L hip yaw lid |  |
| FAIL | L yaw bracket | a feature under 1 mm, 35.3 mm3 |
| PASS | L hip roll lid |  |
| PASS | L roll bracket |  |
| PASS | L thigh frame |  |
| PASS | L hip pitch lid |  |
| PASS | L knee lid |  |
| PASS | L shin |  |
| PASS | L shoe |  |
| PASS | L sole |  |
| PASS | L inner ear |  |
| PASS | chassis |  |
| PASS | neck column |  |
| PASS | neck lid |  |
| PASS | head pitch lid |  |
| PASS | head fork |  |
| FAIL | head yaw bracket | a feature under 1 mm, 12.3 mm3 |
| PASS | head roll lid |  |
| PASS | head roll spacer |  |
| PASS | head roll rear spacer |  |
| FAIL | head frame | a feature under 1 mm, 15.4 mm3 |
| PASS | jaw |  |
| PASS | jaw soft insert |  |
| PASS | face |  |
| PASS | eye ring |  |
| PASS | eye iris |  |

## FIT

| status | item | detail |
|---|---|---|
| PASS | L hip yaw lid | 52 x 32 x 4 mm |
| PASS | L yaw bracket | 42 x 31 x 63 mm |
| PASS | L hip roll lid | 4 x 32 x 52 mm |
| PASS | L roll bracket | 39 x 37 x 24 mm |
| PASS | L thigh frame | 82 x 47 x 62 mm |
| PASS | L hip pitch lid | 52 x 4 x 32 mm |
| PASS | L knee lid | 32 x 4 x 52 mm |
| PASS | L shin | 32 x 43 x 80 mm |
| PASS | L shoe | 70 x 54 x 30 mm |
| PASS | L sole | 70 x 54 x 16 mm |
| PASS | L inner ear | 50 x 5 x 30 mm |
| PASS | chassis | 102 x 66 x 53 mm |
| PASS | neck column | 32 x 50 x 47 mm |
| PASS | neck lid | 32 x 4 x 10 mm |
| PASS | head pitch lid | 32 x 4 x 10 mm |
| PASS | head fork | 49 x 55 x 74 mm |
| PASS | head yaw bracket | 42 x 50 x 39 mm |
| PASS | head roll lid | 4 x 52 x 32 mm |
| PASS | head roll spacer | 4 x 21 x 21 mm |
| PASS | head roll rear spacer | 7 x 21 x 21 mm |
| PASS | head frame | 182 x 132 x 66 mm |
| PASS | jaw | 109 x 136 x 49 mm |
| PASS | jaw soft insert | 36 x 132 x 6 mm |
| PASS | face | 5 x 130 x 66 mm |
| PASS | eye ring | 15 x 45 x 45 mm |
| PASS | eye iris | 13 x 26 x 26 mm |
