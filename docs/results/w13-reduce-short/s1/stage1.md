| Q | how | out (#272) | reasoning (#272) | answer tok (#272) | wall s (#272) | first claim s | refs | unknown / mismatch / dropped | text claims | nnf model / rendered (#272 final) | outside matrix | model-text figures outside matrix |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | called | 5377 (7272) | 3983 (4142) | 1394 (3130) | 72.14 (38.61) | 62.12 | 33 | 0 / 0 / 0 | 0 | 0 / 0 (0) | 0 | 3 |
| Q10 | called | 22555 (24330) | 15409 (17733) | 7146 (6597) | 254.48 (137.25) | 201.72 | 90 | 0 / 0 / 0 | 1 | 0 / 0 (1) | 0 | - |
| Q19 | called | 26481 (21036) | 21821 (12064) | 4660 (8972) | 310.48 (117.14) | 276.52 | 85 | 0 / 0 / 0 | 7 | 0 / 0 (0) | 0 | - |
| Q21 | called | 42063 (57498) | 29492 (36357) | 12571 (21141) | 448.77 (302.7) | 357.77 | 212 | 0 / 0 / 0 | 5 | 3 / 0 (5) | 0 | - |
| Q24 | called | 27468 (27328) | 23823 (17824) | 3645 (9504) | 308.09 (152.69) | 282.62 | 64 | 1 / 0 / 1 | 2 | 0 / 0 (2) | 0 | - |
| Q26 | called | 21890 (22906) | 19098 (16128) | 2792 (6778) | 248.44 (130.72) | 230.08 | 54 | 0 / 0 / 0 | 0 | 0 / 0 (0) | 0 | 900, 900, 40 |

```json
{
 "questions": [
  "Q5",
  "Q10",
  "Q19",
  "Q21",
  "Q24",
  "Q26"
 ],
 "summary": {
  "v6_out": [
   24518.0,
   27468,
   42063
  ],
  "v6_reasoning": [
   20459.5,
   23823,
   29492
  ],
  "v6_answer_tokens": [
   4152.5,
   7146,
   12571
  ],
  "v6_wall": [
   281.28499999999997,
   310.48,
   448.77
  ],
  "v6_ttft": [
   3.13,
   5.3,
   5.52
  ],
  "v6_first_claim": [
   253.3,
   282.62,
   357.77
  ],
  "v6_nnf_sum": 3,
  "v6_outside_matrix_sum": 0,
  "v6_uncited_shown_sum": 0,
  "v6_r_unknown_ref_sum": 1,
  "v6_r_ref_part_mismatch_sum": 0,
  "v6_r_dropped_sum": 1,
  "v6_r_uncited_sum": 0,
  "v6_r_rendered_outside_sum": 0,
  "v6_r_model_outside_sum": 4,
  "v6_r_rendered_number_not_found_sum": 0,
  "v6_r_model_number_not_found_sum": 3,
  "v6_r_text_claims_sum": 15,
  "v6_r_refs_sum": 538,
  "v6_reduce_usd": 0.394,
  "v6_reduce_usd_at_peak": 0.788,
  "v6_periods": {
   "off_peak": 6
  },
  "v6_cut_invalid_failed": 0,
  "v6_fallback_questions": [],
  "272_out": [
   23618.0,
   27328,
   57498
  ],
  "272_reasoning": [
   16930.5,
   17824,
   36357
  ],
  "272_answer_tokens": [
   7875.0,
   9504,
   21141
  ],
  "272_wall": [
   133.985,
   152.69,
   302.7
  ],
  "272_ttft": [
   2.6550000000000002,
   3.06,
   4.2
  ],
  "272_first_claim": [
   null,
   null,
   null
  ],
  "272_nnf_sum": 8,
  "272_outside_matrix_sum": 0,
  "272_uncited_shown_sum": 0,
  "272_r_unknown_ref_sum": 0,
  "272_r_ref_part_mismatch_sum": 0,
  "272_r_dropped_sum": 0,
  "272_r_uncited_sum": 0,
  "272_r_rendered_outside_sum": 0,
  "272_r_model_outside_sum": 0,
  "272_r_rendered_number_not_found_sum": 0,
  "272_r_model_number_not_found_sum": 0,
  "272_r_text_claims_sum": 0,
  "272_r_refs_sum": 0,
  "272_reduce_usd": 0.4131,
  "272_reduce_usd_at_peak": 0.8262,
  "272_periods": {
   "off_peak": 6
  },
  "272_cut_invalid_failed": 0,
  "272_fallback_questions": []
 },
 "stage1": {
  "checks": {
   "unknown_ref == 0": false,
   "ref_part_mismatch == 0": true,
   "no_citation before the move == 0": true,
   "outside_matrix == 0": true,
   "cut / invalid / failed == 0": true,
   "number_not_found in model text <= 8": true,
   "number_not_found in rendered text == 0": true,
   "output p50 <= 0.60 x 23618.0 = 14171": false,
   "wall p50 <= 0.70 x 133.985 = 93.8": false
  },
  "continue": false
 }
}
```
