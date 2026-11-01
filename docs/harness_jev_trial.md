# Harness–Jev–Mesa organizational trial

The official Harness host creates and operates an organizational-learning experiment through MCP. Six worlds compare siloed and bridge contacts using seeds 7, 8 and 9. Each world has 1,000 members, four departments and six rounds. Jev 1.14.0 returns 36,000 fresh judgments, using native batches of 64 with concurrency 4 and a $1 client allowance.

Siloed final performances are 49.7053, 54.4110 and 65.8815; bridge performances are 54.4205, 66.6235 and 76.5459. Mean performance is 56.6659 versus 65.8633, with mean exploration 14.244% versus 10.650%. All 36 period metrics match saved-probability replay. Event inspection verifies a recorded copy action for world 0, round 2, agent 0.

The 576 requests comprise 540 batches of 64 and 36 of 40. Returned input usage is 18,963,055 tokens, metered at the configured $0.042 per million: $0.79644831. Summed simulation execution is 214.48 seconds, and complete Harness wall time 307.22 seconds. Median request latency is 1.344 seconds and maximum 2.454 seconds.

The assistant uses 20 model steps and 19 tool calls, including 15 status queries. Host usage is 63,512 uncached input, 225,664 cached input and 4,637 output tokens, totaling 293,813; gateway charges were not priced. The audit file preserves individual worlds, receipts and replay checks. This run measures a concrete joint research workflow, with each member receiving a new judgment each round.

## Configuration and execution

| Contact structure | Seed | Round-6 per-member performance | Whole-run exploration share |
| --- | ---: | ---: | ---: |
| siloed | 7 | 49.7053 | 0.1415 |
| siloed | 8 | 54.4110 | 0.1332 |
| siloed | 9 | 65.8815 | 0.1527 |
| bridge | 7 | 54.4205 | 0.1125 |
| bridge | 8 | 66.6235 | 0.1052 |
| bridge | 9 | 76.5459 | 0.1018 |

| Item | Measured value |
| --- | ---: |
| Fresh decisions | 36,000 |
| Successful native Jev batches | 576 |
| Batch composition | 540 batches × 64 questions; 36 batches × 40 questions |
| Jev returned input tokens | 18,963,055 |
| Recorded Jev cost | $0.79644831 |
| Summed simulation time across six worlds | 214.48 seconds |
| Harness process wall time | 307.22 seconds |
| Jev batch latency median / maximum | 1.344 / 2.454 seconds |
| Harness steps / tool calls | 20 / 19 |

## Sources and records

- [harness_trial.md](harness_trial.md)
