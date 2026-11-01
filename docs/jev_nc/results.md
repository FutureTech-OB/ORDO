# Nature Communications pilot results

The group runs 20 worlds and 1,471 fresh Jev judgments. Repeated games initialized with CC, CD or DD history have final-three-round mutual-cooperation rates of 16.7%, 0 and 12.5%. This substitutes an untrained decision policy into the interaction environment.

The reputation/reward case yields final analytical expected cooperation of 0%, 93.23% and 98.44% at information parameters 0, 0.5 and 1. These are consequences of selected strategies in the source analytical-payoff environment. In collective foraging, social cues change group reward by −4.5 on clustered maps and −1.5 on random maps under the pilot menu and horizon. Per-condition records retain all outcomes.

## Configuration and execution

| Item | Actual records | Interpretation |
|---|---:|---|
| Returned model | `typesafe/jev-1.14-20261014` | typesafe/jev-1.14 via OpenRouter native decisions |
| Completed worlds | 20 | Repeated games 6, reputation 6, foraging 8; two environment seeds per condition |
| Fresh choices | 1,471 | Repeated games 576, strategy revision 576, foraging targets 319; fresh choices without source-action fallback |
| Requests | 53 successful / 53 attempted | Native batching, no retries or failed transports; 1,471 decisions are not HTTP requests |
| Provider-reported cost | US$0.027672288 | Sum of usage.cost, excluding development, compute and network expenses |
| live SDKTime | 61.134 seconds | Includes API waits, environment updates, logging and empty post-termination stages |
| Total attempt time | 61.970 seconds | Includes offline replay and result export |
| Replay | All inputs and metrics match exactly | Saved probabilities replay the same environment and sampling protocol, verifying recorded execution without new service calls. |

| Initial events | Final-window individual cooperation | Final-window mutual cooperation |
|---|---:|---:|
| CC | 39.58% | 16.67% (4 / 24 pair-round) |
| CD | 20.83% | 0% (0 / 24) |
| DD | 29.17% | 12.50% (3 / 24) |

| Information transmission λ | Analytical expected cooperation | Share using reward-cooperators-only strategies |
|---|---:|---:|
| 0 | 0% | 6.25% |
| 0.5 | 93.23% | 96.875% |
| 1 | 98.4375% | 100% |

| Map | Explicit social cues | Mean group reward across two worlds | Mean revealed cells |
|---|---|---:|---:|
| smooth | Off | 12 | 36.5 |
| smooth | On | 7.5 | 36 |
| random | Off | 9.5 | 34.5 |
| random | On | 8 | 37 |

## Sources and records

- [Pilot coverage report (JSON)](../jev_validation/coverage.json)
- [Nature Communications pilot analysis (JSON)](../jev_validation/nc_analysis.json)
- Per-case results: `../../runs/jev-nc-20261030/case_results.json` (local run artifact)
- [Nature Communications pilot configuration (JSON)](../jev_validation/nc_plan.json)
- [Su et al., *Nature Communications*17:490](https://www.nature.com/articles/s41467-025-67178-6)
- [Pal & Hilbe, *Nature Communications*13:5928](https://www.nature.com/articles/s41467-022-33551-y)
- [Wu et al., *Nature Communications*16:3539](https://www.nature.com/articles/s41467-025-58365-6)
