## docs/results/w12-latency/b-fts/raw
545 calls (545 off-peak, 0 peak as billed): billed $15.56 ($0.519/q); all off-peak $15.56 ($0.519/q); all peak $31.12 ($1.037/q)
| part | tokens | off-peak $ | peak $ |
|---|---|---|---|
| map input_hit | 600,320 | 0.01 | 0.03 |
| map input_miss | 15,058,288 | 9.94 | 19.88 |
| map output | 1,952,192 | 3.87 | 7.73 |
| plan input_hit | 32,256 | 0.00 | 0.00 |
| plan input_miss | 7,831 | 0.01 | 0.01 |
| plan output | 14,638 | 0.03 | 0.06 |
| reduce input_hit | 47,744 | 0.00 | 0.00 |
| reduce input_miss | 547,328 | 0.36 | 0.72 |
| reduce output | 602,621 | 1.19 | 2.39 |
| remap input_hit | 44,928 | 0.00 | 0.00 |
| remap input_miss | 175,618 | 0.12 | 0.23 |
| remap output | 18,507 | 0.04 | 0.07 |

## docs/results/w13-prefix-cache/b-fts/raw
548 calls (320 off-peak, 228 peak as billed): billed $16.85 ($0.562/q); all off-peak $11.95 ($0.398/q); all peak $23.89 ($0.796/q)
| part | tokens | off-peak $ | peak $ |
|---|---|---|---|
| map input_hit | 15,100,416 | 0.33 | 0.66 |
| map input_miss | 10,197,565 | 6.73 | 13.46 |
| map output | 1,652,835 | 3.27 | 6.55 |
| plan input_hit | 32,256 | 0.00 | 0.00 |
| plan input_miss | 7,831 | 0.01 | 0.01 |
| plan output | 14,638 | 0.03 | 0.06 |
| reduce input_hit | 50,048 | 0.00 | 0.00 |
| reduce input_miss | 456,008 | 0.30 | 0.60 |
| reduce output | 534,997 | 1.06 | 2.12 |
| remap input_hit | 57,088 | 0.00 | 0.00 |
| remap input_miss | 249,141 | 0.16 | 0.33 |
| remap output | 24,633 | 0.05 | 0.10 |

