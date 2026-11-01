# Archived LLM-simulation verification

Author-record replay covers 39 naming-game experiments, 12,449 pair encounters and 22,622 nonfixed-member decisions. ORDO regenerates the same interaction records, final personal histories and payoffs. The replay engine receives the original event's saved choice, while the environment reconstructs observations and commits the resulting actions.

The verification export also records the majority-coordination adapter and its reference checks. Tables and manifests identify which results use source actions, rule policies or new model judgments. Fresh Jev behavior results are documented separately.

## Configuration and execution

| SourceCondition | Experiments | Pair encounters | Nonfixed-member choices |
| --- | ---: | ---: | ---: |
| minority_4_Q_to_M | 6 | 4,127 | 6,844 |
| minority_5_Q_to_M | 6 | 2,001 | 3,136 |
| spontaneous_W10 | 27 | 6,321 | 12,642 |

| File / segment | Recorded rows | Step range | Final coordination | Interpretation |
| --- | ---: | --- | ---: | --- |
| 0_50_0.2_0.0_claude-3-haiku-20240307 / 0 | 1000 | 0–999 | 0.52 | No consensus within recorded horizon |
| 0_50_0.2_0.0_claude-3-opus-20240229 / 0 | 249 | 0–248 | 1.00 | Consensus observed |
| 0_50_0.2_0.0_gpt-3.5-turbo-1106 / 0 | 1000 | 0–999 | 0.12 | No consensus within recorded horizon |
| 0_50_0.2_0.0_gpt-4-turbo-2024-04-09 / 0 | 41 | 0–40 | 0.20 | No consensus within recorded horizon |
| 0_50_0.2_0.0_gpt-4-turbo-2024-04-09 / 1 | 271 | 0–270 | 1.00 | Consensus observed |
| 0_50_0.2_0.0_gpt-4-turbo-2024-04-09 / 2 | 3 | 270–272 | 1.00 | Nonzero overlapping fragments |
| 9_50_0.2_0.0_meta-llama-3-70b-instruct / 0 | 500 | 0–499 | 0.68 | No consensus within recorded horizon |

| Interface | Scenario | Offline decisions | Mock HTTP requests | Network requests |
| --- | --- | ---: | ---: | ---: |
| jev | naming | 8 | 4 | 0 |
| jev | opinion | 4 | 4 | 0 |
| chat | naming | 8 | 8 | 0 |
| chat | opinion | 4 | 4 | 0 |

## Sources and records

- [verification.json](verification.json)
- [Published LLM social simulations through ORDO](README.md)
