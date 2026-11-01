# Repeated games: historical argmax arm

This record describes the earlier deterministic arm. The current default is raw-probability sampling, documented in nhb_sampled_results.md. The historical argmax arm chose defection in all 320 model decisions; the source GPT-4 archive cooperated in 204/320 choices. Payoffs and full ordered-match results remain in the accompanying machine-readable files.

The twenty-round histories and all 64 ordered matches were executed using the same source feedback rules. Raw provider probabilities, applied one-hot argmax choices, source traces, and replay checks were recorded. Thirty-one frozen implementation files preserve that arm's original source state. The sampling arm obtains new model judgments following its changed feedback trajectory.

## Configuration and execution

| Item | Observed value |
|---|---:|
| Complete source condition | 64 ordered pairs × 20 rounds = 1,280 game rounds |
| All actions from both players | 2,560 total actions; 320 are fresh Jev judgments |
| Matches involving Jev | 15 pairs; self-play has two model roles, giving 16 perspectives |
| Fresh Jev choices | **320**; the other 49 pairs retain free-rule baselines |
| Successful / attempted requests | 300 / 301; one transient transport failure retried successfully |
| Returned model identifier | `typesafe/jev-1.14-20261014` |
| Sum of provider usage.cost | **US$0.0110901** |
| Client reserve for uncertain failed requests | US$0.00013734; metered estimate |
| Elapsed time | **340.085 seconds**, including retries, free matches, analysis and replay |
| Provider input/output tokens | 264,050 / 17,196 |

| Ordered match pairs | New-run payoff P1/P2 | Archived GPT-4 payoff P1/P2 |
|---|---:|---:|
| Jev → Jev | 100 / 100 | 160 / 160 |
| Jev → TFT | 105 / 95 | 160 / 160 |
| Jev → TFTT | 105 / 95 | 160 / 160 |
| Jev → STFT | 100 / 100 | 100 / 100 |
| Jev → RTFT | 195 / 5 | 115 / 115 |
| Jev → HTFT | 100 / 100 | 95 / 105 |
| Jev → NP10 | 105 / 95 | 106 / 106 |
| Jev → NP20 | 105 / 95 | 119 / 129 |
| TFT → Jev | 95 / 105 | 160 / 160 |
| TFTT → Jev | 95 / 105 | 160 / 160 |
| STFT → Jev | 100 / 100 | 100 / 100 |
| RTFT → Jev | 5 / 195 | 115 / 115 |
| HTFT → Jev | 100 / 100 | 110 / 90 |
| NP10 → Jev | 95 / 105 | 127 / 127 |
| NP20 → Jev | 95 / 105 | 124 / 124 |

## Sources and records

- [Repeated games: raw-probability sampling results](nhb_sampled_results.md)
- [Playing repeated games with large language models](https://www.nature.com/articles/s41562-025-02172-y)
- [Repeated games: the source SI B.2 tournament](nhb_original.md)
- verification.json: `../../runs/llm-nhb-original-20261030/verification.json` (local run artifact)
- Source-loop trace: `../../runs/llm-nhb-original-20261030/source_trace.json` (local run artifact)
- Result analysis: `../../runs/llm-nhb-original-20261030/analysis.json` (local run artifact)
- Recorded experiment configuration: `../../runs/llm-nhb-original-20261030/plan-before-calls.json` (local run artifact)
- [CSV](nhb_jev_matches.csv)
- [JSON](nhb_results_summary.json)
