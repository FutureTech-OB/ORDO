# Historical gateway integration test

On 15 October 2026, the compatible gateway at api-int.memtensor.cn/v1 authenticated and served deepseek-v4.1-flash. A probe and two eight-member, three-round worlds produced 48 valid fresh choices. All responses matched recorded actions, and six period metrics matched action replay. Simulation plus free-rule reference execution took 17.78 seconds.

The baseline has no guidance or failure penalty; the joint intervention encourages exploration and sets a failure penalty of 10. Exploration is 8.33% versus 29.17%, final performance 14.62 versus 15.15, and cumulative net payoff 36.75 versus 30.80. Each condition uses seed 7, two departments and bridge contacts.

The assistant generated a plan, submitted it through the official Python MCP client, and summarized results. An initial plan guessed unsupported fields and was rejected; explicit scenario/base/vary/seeds/decision schemas enabled a valid second plan. A summary overgeneralized a final-round count, motivating whole_run and metric_scope output fields. That wording change was not rerun through the paid gateway.

Across the probe, 48 decisions and three assistant requests, 52 API requests returned 42,565 input and 1,216 output tokens. Gateway prices were not verified. Nineteen tests and MCP protocol checks passed at this stage. This historical connectivity test precedes the confirmed architecture: Harness assists research, Jev or rules supply simulation choices, and the ABM computes outcomes. Raw responses remain local; the repository contains the account only.

## Configuration and execution

| Scenario | Valid choices | Whole-run exploration rate | Final per-member performance | Per-member cumulative net payoff |
| --- | --- | --- | --- | --- |
| baseline | 24/24 | 8.33% | 14.62 | 36.75 |
| guidance_penalty | 24/24 | 29.17% | 15.15 | 30.80 |

## Sources and records

- [harness_trial.md](harness_trial.md)
