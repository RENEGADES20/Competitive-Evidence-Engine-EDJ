# #250 fts: 0-call count, cap and map message-hash check (before the fts run)

Planner phase: `fts-plan` (main 08b0ac4 at af4aa99), real_calls 22, reused 8, every plan source `model`, new USD 0.307.
Allow-list cache `cache-fts-final`: 88 committed records (48 inherited map / remap records left out: not served or not checked) + the 22 new plans.
Final count `count2-fts` (52aff03, --max-calls 0, key empty): real_calls 0, reused 67.

# fts count C-fts (count2-fts, main 08b0ac4)

From `count2-fts\report.json` (0 calls; meta.real_calls 0, reused 67).

| Q | plan | sub-q | round-1 maps served | round-1 to make | row keys (non-comparison) | remaps served | round-2 bound | reduce | reduce to make | cap |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | cached: Q1-plan-2842fd95a4bd | 5 | 1 | 0 | MS | 0 | 1 | cap | 1 | 2 |
| Q2 | cached: Q2-plan-1c13be5ec7a6 | 7 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q3 | cached: Q3-plan-751ecc3596a7 | 5 | 1 | 0 | SCHW | 0 | 1 | cap | 1 | 2 |
| Q4 | cached: Q4-plan-82545e2a7b7f | 12 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |
| Q5 | cached: Q5-plan-ba18bc1a7fbf | 1 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q6 | cached: Q6-plan-0a8df5867283 | 3 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q7 | cached: Q7-plan-5dfaf706584d | 21 | 0 | 4 | MER, MS, RJF | 0 | 3 | code_built | 1 | 8 |
| Q8 | cached: Q8-plan-43c66da6bf28 | 4 | 0 | 2 | RJF, SCHW | 0 | 2 | code_built | 1 | 5 |
| Q9 | cached: Q9-plan-a963b7a4c0a8 | 10 | 0 | 2 | MER, MS | 0 | 2 | code_built | 1 | 5 |
| Q10 | cached: Q10-plan-ec78e571764 | 10 | 0 | 6 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 12 |
| Q11 | cached: Q11-plan-10d2767ebe7 | 20 | 5 | 0 | EDJ, MER, MS, RJF, SCHW | 2 | 3 | cap | 1 | 4 |
| Q12 | cached: Q12-plan-3c795856ff6 | 8 | 0 | 2 | EDJ, SCHW | 0 | 2 | code_built | 1 | 5 |
| Q13 | cached: Q13-plan-378afa8a249 | 5 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q14 | cached: Q14-plan-b25fe402463 | 8 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q15 | cached: Q15-plan-82186d401f1 | 10 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q16 | cached: Q16-plan-6c86ffcde7f | 11 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q17 | cached: Q17-plan-947690fbef6 | 7 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q18 | cached: Q18-plan-8b4b10bfb12 | 2 | 0 | 1 |  | 0 | 0 | code_built | 1 | 2 |
| Q19 | cached: Q19-plan-fa97302df6c | 65 | 4 | 0 | EDJ, MER, MS, RJF, SCHW | 3 | 2 | cached | 0 | 2 |
| Q20 | cached: Q20-plan-3a1787ce9cf | 6 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q21 | cached: Q21-plan-f2cc541f326 | 80 | 0 | 6 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 12 |
| Q22 | cached: Q22-plan-cbce9d55f95 | 10 | 5 | 0 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | cap | 1 | 6 |
| Q23 | cached: Q23-plan-1b401760014 | 5 | 5 | 0 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | cached | 0 | 5 |
| Q24 | cached: Q24-plan-9998b66bd82 | 20 | 5 | 0 | EDJ, MER, MS, RJF, SCHW | 1 | 4 | cap | 1 | 5 |
| Q25 | cached: Q25-plan-17c16379324 | 30 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q26 | cached: Q26-plan-b3e8c05eb52 | 8 | 1 | 0 | RJF | 1 | 0 | cached | 0 | 0 |
| Q27 | cached: Q27-plan-7d9cf938c1a | 13 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |
| Q28 | cached: Q28-plan-7fd84151946 | 6 | 0 | 3 | EDJ, MER | 0 | 2 | code_built | 1 | 6 |
| Q29 | cached: Q29-plan-f692994e5bd | 2 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q30 | cached: Q30-plan-5cc5df215e8 | 3 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |

**Cap = 139** (round-1 48 + round-2 bound 64 + reduces 27).

## Map message hashes: inherited records reused at the final count vs their producing commit (C2, C3)

now: 52aff03 (count2-fts.tsv)

| record | served now | producing source | message | system | schema | request | result |
|---|---|---|---|---|---|---|---|
| `Q1-map.MS-56c4e1e3716ff6c3ba1b4e56.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q3-map.SCHW-0054c9b03093520057275e0b.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q11-map.MS-be5abb84931a01eb70244e66.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-map.SCHW-50b1a0ad5bbf76893e5f8484.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-map.EDJ-cc121b1d4c81e376986988e7.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-map.RJF-ad9eb64b2db2dbce4a66cc45.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-map.MER-276f18586be07516f2c61699.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-remap.MS-8aef2b7c956ec7a324c8012a.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q11-remap.MER-02eeaf9cd5d8691c3a4b0057.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-map.EDJ-d4ee755791049c092804bcaa.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-map.research-37496b821ecf0dc5abba1a69.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-map.MER-e3631fa2ddc0271b89ed15e4.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-map.SCHW-e4e157d52a5ef74d082cfe8e.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-remap.MER-6a89d75baa2e2b6d832a1069.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-remap.EDJ-882898781e5b8579efa0a0a3.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q19-remap.RJF-13e5919f6652f7d88ddf08f5.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q22-map.MS-3ec45f9ace0291d80f83e88f.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q22-map.SCHW-1b66ef7652486a68d1ac4a00.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q22-map.EDJ-97f070c4b99c2a1ff222b8a9.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q22-map.MER-68c9b5a3ed410ed31ca5c711.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q22-map.RJF-c26ee68159907e836ef2cad4.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q23-map.SCHW-c4ce1607deedb92e46a647fb.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q23-map.MER-760c08d0605fe7c753873c23.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q23-map.EDJ-345ae75ccd0523bda816dc3d.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q23-map.MS-73f2cfc25eea627b91c8e6d0.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q23-map.RJF-44a0731d9503112c16bd07f8.json` | reused | hist-2d5f25b | same | same | same | same | match: allowed |
| `Q24-map.MS-e79e88ab824a959038edc3ce.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q24-map.SCHW-e4e2007e520b85a39f236f83.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q24-map.EDJ-c84925c7c7e572d0b92989cb.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q24-map.MER-b9ba10d5838609b72da8e87a.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q24-map.RJF-10dab7f4fd7529df88adf7ea.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q24-remap.SCHW-25fe91c4562fbc0b0bb27487.json` | reused | hist-715adda | same | same | same | same | match: allowed |
| `Q26-map.RJF-4a8e75c71429042954fd27cf.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |
| `Q26-remap.RJF-da575072e1012429783bd587.json` | reused | hist-7b9a5b4 | same | same | same | same | match: allowed |

Inherited records reused now: 34; hash match (allowed): 34; differ: 0; no source hash: 0.

<details><summary>Producing commit per inherited map record, from its `at` (C2)</summary>

```text
record	at	producing
Q1-map.MS-56c4e1e3716ff6c3ba1b4e56.json	2026-11-20T02:49:05.931186	hist-7b9a5b4
Q11-map.EDJ-4ebc6aa31bb63d10a18bfa3f.json	2026-11-20T03:00:16.156555	hist-7b9a5b4
Q11-map.EDJ-832e00edb45ce15d122f6e5e.json	2026-11-20T00:14:35.622783	None
Q11-map.EDJ-cc121b1d4c81e376986988e7.json	2026-11-20T06:57:05.903319	hist-715adda
Q11-map.MER-1ca22e1aa9f894f6c827a311.json	2026-11-20T00:14:35.623904	None
Q11-map.MER-276f18586be07516f2c61699.json	2026-11-20T06:57:05.905331	hist-715adda
Q11-map.MER-9a0e05418da23747fc9a1221.json	2026-11-20T03:00:16.160573	hist-7b9a5b4
Q11-map.MS-44e26f02e59aec8a26fb89ae.json	2026-11-20T03:00:16.146561	hist-7b9a5b4
Q11-map.MS-85586c13eb7f89a2c2b1c55b.json	2026-11-20T00:14:35.619762	None
Q11-map.MS-be5abb84931a01eb70244e66.json	2026-11-20T06:57:05.871950	hist-715adda
Q11-map.RJF-639e2a4e4d933caac3372168.json	2026-11-20T03:00:16.199440	hist-7b9a5b4
Q11-map.RJF-ac0e96f2f1d67203f8bda36b.json	2026-11-20T00:14:35.624832	None
Q11-map.RJF-ad9eb64b2db2dbce4a66cc45.json	2026-11-20T06:57:05.923374	hist-715adda
Q11-map.SCHW-50b1a0ad5bbf76893e5f8484.json	2026-11-20T06:57:05.874083	hist-715adda
Q11-map.SCHW-98222adb7d6f5efe452b7f3d.json	2026-11-20T00:14:35.620811	None
Q11-map.SCHW-e373945a82a28c26ae739cff.json	2026-11-20T03:00:16.151561	hist-7b9a5b4
Q11-remap.EDJ-44f5932f4805318982c60933.json	2026-11-20T03:06:52.024761	hist-7b9a5b4
Q11-remap.MER-02eeaf9cd5d8691c3a4b0057.json	2026-11-20T03:06:52.028894	hist-7b9a5b4
Q11-remap.MER-dfc417f36ed19a64f55671ea.json	2026-11-20T00:22:49.091540	None
Q11-remap.MS-8aef2b7c956ec7a324c8012a.json	2026-11-20T07:02:03.934555	hist-715adda
Q11-remap.MS-c42795edd37bcb0821982b51.json	2026-11-20T00:22:49.086541	None
Q11-remap.MS-e6eb3d8fdc49c6436da4f0ba.json	2026-11-20T03:06:52.023135	hist-7b9a5b4
Q19-map.EDJ-d4ee755791049c092804bcaa.json	2026-11-20T03:11:25.885786	hist-7b9a5b4
Q19-map.EDJ-e4a10aba1f757f3a559368a4.json	2026-11-20T00:25:50.248541	None
Q19-map.MER-58a445d8bd4ccaf0c0f5ad36.json	2026-11-20T00:25:50.251554	None
Q19-map.MER-e3631fa2ddc0271b89ed15e4.json	2026-11-20T03:11:25.889066	hist-7b9a5b4
Q19-map.research-309b4a9a068ab205b58305c5.json	2026-11-20T00:25:50.260683	None
Q19-map.research-37496b821ecf0dc5abba1a69.json	2026-11-20T03:11:25.963652	hist-7b9a5b4
Q19-map.SCHW-76e14baeca02e6a8f06a5f8b.json	2026-11-20T00:25:50.249555	None
Q19-map.SCHW-e4e157d52a5ef74d082cfe8e.json	2026-11-20T03:11:25.887040	hist-7b9a5b4
Q19-remap.EDJ-7eac6ae4e38d42a01629c7f3.json	2026-11-20T00:31:34.382679	None
Q19-remap.EDJ-882898781e5b8579efa0a0a3.json	2026-11-20T03:17:53.436697	hist-7b9a5b4
Q19-remap.MER-6a89d75baa2e2b6d832a1069.json	2026-11-20T03:17:53.465160	hist-7b9a5b4
Q19-remap.MER-8696c68687048d40288ed0a8.json	2026-11-20T00:31:34.399373	None
Q19-remap.RJF-13e5919f6652f7d88ddf08f5.json	2026-11-20T03:17:53.472336	hist-7b9a5b4
Q19-remap.RJF-477732136eb4e03ca8c18d35.json	2026-11-20T00:31:34.409913	None
Q22-map.EDJ-97f070c4b99c2a1ff222b8a9.json	2026-11-20T03:23:56.484536	hist-7b9a5b4
Q22-map.MER-68c9b5a3ed410ed31ca5c711.json	2026-11-20T03:23:56.489533	hist-7b9a5b4
Q22-map.MS-3ec45f9ace0291d80f83e88f.json	2026-11-20T07:12:25.886875	hist-715adda
Q22-map.MS-5d77dcbe36e50468bc861995.json	2026-11-20T03:23:56.471113	hist-7b9a5b4
Q22-map.RJF-c26ee68159907e836ef2cad4.json	2026-11-20T03:23:56.495532	hist-7b9a5b4
Q22-map.SCHW-1b66ef7652486a68d1ac4a00.json	2026-11-20T03:23:56.477368	hist-7b9a5b4
Q23-map.EDJ-232e30d58182ebf97220cece.json	2026-11-20T03:32:30.934313	hist-7b9a5b4
Q23-map.EDJ-345ae75ccd0523bda816dc3d.json	2026-11-20T07:18:33.990434	hist-715adda
Q23-map.EDJ-b62a88d9b8ee87e8ba08283d.json	2026-11-20T00:31:58.733534	None
Q23-map.MER-142c7b0b45454d83f276f254.json	2026-11-20T00:31:58.742406	None
Q23-map.MER-51dc8849016df7b836ee3996.json	2026-11-20T03:32:30.944893	hist-7b9a5b4
Q23-map.MER-760c08d0605fe7c753873c23.json	2026-11-20T07:18:34.050966	hist-715adda
Q23-map.MS-1ec3753a1e771e1670f574fa.json	2026-11-20T03:32:30.929817	hist-7b9a5b4
Q23-map.MS-73f2cfc25eea627b91c8e6d0.json	2026-11-20T07:18:33.987198	hist-715adda
Q23-map.MS-c93d86687251ce9a3cf46819.json	2026-11-20T00:31:58.730543	None
Q23-map.RJF-44a0731d9503112c16bd07f8.json	2026-11-20T12:49:07.879183-06:00	hist-2d5f25b
Q23-map.RJF-617005416e4477d9351930fd.json	2026-11-20T00:31:58.740537	None
Q23-map.RJF-737ba0e1fd498dc30818af83.json	2026-11-20T03:32:30.952726	hist-7b9a5b4
Q23-map.RJF-a063e658132744c7d7adb3c5.json	2026-11-20T07:18:34.093838	hist-715adda
Q23-map.SCHW-23a95ff51db88ffd6b4d0b86.json	2026-11-20T00:31:58.731534	None
Q23-map.SCHW-b120a46625ab480a5fe47b46.json	2026-11-20T03:32:30.930817	hist-7b9a5b4
Q23-map.SCHW-c4ce1607deedb92e46a647fb.json	2026-11-20T07:18:33.988118	hist-715adda
Q24-map.EDJ-74e266b8ea3e873eadb79b58.json	2026-11-20T00:37:35.695556	None
Q24-map.EDJ-bdfcca2016216cba46058cde.json	2026-11-20T03:45:02.970533	hist-7b9a5b4
Q24-map.EDJ-c84925c7c7e572d0b92989cb.json	2026-11-20T07:26:21.597935	hist-715adda
Q24-map.MER-0dd01a4557ed209e9916948b.json	2026-11-20T00:37:35.701375	None
Q24-map.MER-4149983cb7a80b10b80cba81.json	2026-11-20T03:45:02.992487	hist-7b9a5b4
Q24-map.MER-b9ba10d5838609b72da8e87a.json	2026-11-20T07:26:21.633166	hist-715adda
Q24-map.MS-5d4c90f888d8cda7118ac076.json	2026-11-20T03:45:02.966490	hist-7b9a5b4
Q24-map.MS-92aa4d52ec9710da624112cb.json	2026-11-20T00:37:35.589972	None
Q24-map.MS-e79e88ab824a959038edc3ce.json	2026-11-20T07:26:21.588217	hist-715adda
Q24-map.RJF-10dab7f4fd7529df88adf7ea.json	2026-11-20T07:26:21.666019	hist-715adda
Q24-map.RJF-3640ec1f86491103dbe3c4c1.json	2026-11-20T03:45:02.994489	hist-7b9a5b4
Q24-map.RJF-864e3a9f16220a9211fd32d1.json	2026-11-20T00:37:35.709970	None
Q24-map.SCHW-b389f73ef88a6ed59756cf5b.json	2026-11-20T03:45:02.967488	hist-7b9a5b4
Q24-map.SCHW-e4e2007e520b85a39f236f83.json	2026-11-20T07:26:21.594150	hist-715adda
Q24-map.SCHW-f91d9e106d997813c987bc56.json	2026-11-20T00:37:35.599977	None
Q24-remap.MER-240c45c2024878f970cc8639.json	2026-11-20T00:44:42.262984	None
Q24-remap.MER-a4c1ac6f27708f08bf6e9580.json	2026-11-20T03:50:45.871681	hist-7b9a5b4
Q24-remap.SCHW-25fe91c4562fbc0b0bb27487.json	2026-11-20T07:32:40.106470	hist-715adda
Q24-remap.SCHW-e3057d4da5218c116e9b56a6.json	2026-11-20T00:44:42.260911	None
Q26-map.RJF-4a8e75c71429042954fd27cf.json	2026-11-20T03:58:08.967044	hist-7b9a5b4
Q26-map.RJF-e7ab5027269361a96d41c5c2.json	2026-11-20T00:47:31.417875	None
Q26-remap.RJF-da575072e1012429783bd587.json	2026-11-20T04:06:30.598173	hist-7b9a5b4
Q26-remap.RJF-e58e9414f8498c0d60815c76.json	2026-11-20T00:53:51.603576	None
Q3-map.SCHW-0054c9b03093520057275e0b.json	2026-11-20T02:54:52.536593	hist-7b9a5b4
```
</details>
