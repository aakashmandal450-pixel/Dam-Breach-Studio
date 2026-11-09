# Stage 4 results (blind validation, frozen cal-2)

Results manifest: git 353a9e5341f936bf8a7c428ac33c0b54397eb1af

| Case | Qp model / obs | ratio | Tp model / obs [h] | ratio | B model / obs [m] | rel. | No breach | Pass | J |
|---|---|---|---|---|---|---|---|---|---|
| E1S2 | 4.02 / 1.8 | 2.23 | 4.95 / - | - | 2.43 / 6.2 | -0.61 | - | False | 1.01 |
| E2S1 | 1.69 / 2.3 | 0.737 | 2.45 / - | - | 3.09 / 3.3 | -0.065 | - | True | 0.0975 |
| E2S3 | 0.287 / - | - | 27.8 / - | - | 0 / 2.4 | -1 | True | False | 1 |
| IMPACT_1-02 | 440 / 390 | 1.13 | 4.93 / 5.1 | 0.966 | 39.8 / - | - | - | True | 0.0156 |
| IMPACT_2C-02 | 49.7 / 117 | 0.425 | 5.71 / 2.45 | 2.33 | 10.7 / 15 | -0.29 | - | False | 1.53 |
| LaurelRun | 548 / 1.05e+03 | 0.522 | 2.69 / - | - | 27.4 / 35.1 | -0.22 | - | False | 0.472 |
| Poerua | 44.1 / 2.5e+03 | 0.0176 | 0.256 / - | - | 0 / 125 | -1 | - | False | 17.3 |
| Yigong | 1.18e+04 / 9.4e+04 | 0.125 | 19 / 6.17 | 3.08 | 627 / 432 | 0.45 | - | False | 5.78 |

| Limit | cases met / applicable | passes (>= 2/3) |
|---|---|---|
| peak within x1.5 | 2 / 7 | False |
| time to peak within x2 | 1 / 3 | False |
| final width within +/-50 % | 4 / 7 | False |
| no breach reproduced | 1 / 1 | True |
| balance < 1e-6 of volume released | 8 / 8 | True |
| lake drawdown within +/-25 % | 0 / 0 | - |

Cases passing all their limits: 2 of 8; J total 27.216

LOO envelope (min-max over F_all and LOO factor sets):

- E1S2: Qp ratio [0.5907538255795041, 2.2336474404325934], Tp ratio None, B rel [-0.6075268817204301, -0.6075268817204301]
- E2S1: Qp ratio [0.5028072638373904, 0.736844984578633], Tp ratio None, B rel [-0.6150392817059482, -0.06509539842873162]
- E2S3: Qp ratio None, Tp ratio None, B rel [-1.0, -0.1682098765432098]
- IMPACT_1-02: Qp ratio [1.120751151093476, 1.4186960154257144], Tp ratio [0.9659317402144114, 1.005504818359925], B rel None
- IMPACT_2C-02: Qp ratio [0.4249067996617004, 0.7094026898858956], Tp ratio [1.5705951319377383, 2.3286682946002966], B rel [-0.2876712328767123, -0.06849315068493157]
- LaurelRun: Qp ratio [0.27661056209980345, 0.5217257952046402], Tp ratio None, B rel [-0.22070015220700162, -0.22070015220700162]
- Poerua: Qp ratio [0.017631191805801295, 0.017631191805801295], Tp ratio None, B rel [-1.0, -1.0]
- Yigong: Qp ratio [0.1253831126533074, 0.7518120002147225], Tp ratio [1.87595022724723, 3.0800738648620634], B rel [0.14197530864197538, 0.45061728395061745]

IMPACT_1-02 with the WP2 inflow: Qp ratio 1.04, Tp ratio 0.969, B rel -

## Walsh (seen validation, split-5; not in the pass rate)

| Run | Qp model / obs [m3/s] | ratio | t peak from T=0 model / obs [s] | B* at peak model / obs [m] |
|---|---|---|---|---|
| WalshS1__H16 | 0.275 / 0.14 | 1.97 | 91 / 90 | 1.65 / 1.76 |
| WalshS1__H24 | 0.377 / 0.14 | 2.69 | 51 / 90 | 1.97 / 1.76 |
| WalshS3__H16 | 0.343 / 0.24 | 1.43 | 206 / 73 | 1.65 / 1.4 |
| WalshS3__H24 | 0.492 / 0.24 | 2.05 | 122 / 73 | 1.93 / 1.4 |
| WalshS5__H16 | 0.332 / 0.17 | 1.96 | 122 / 93 | 1.84 / 1.29 |
| WalshS5__H24 | 0.547 / 0.17 | 3.22 | 67 / 93 | 1.76 / 1.29 |
