# NC worlds with fresh Jev decisions

`examples.jev_nc.suite.build_cases()` returns 20 independent SDK cases across three original research papers. The caller supplies a **real external Jev engine** to `orgabm.sdk.run_simulation`. These modules contain no Jev credentials, no API calls, no cached probabilities, no author-policy fallback, and no claimed live results. `analyze(case_results)` reports observed directions, including negative and missing findings.

Each case is `{id, paper_id, environment, rounds, seed, condition}`. After running it, pass `{**case, "result": result}` into `analyze`. Exclude the environment object when serializing case metadata. Terminal empty batches in the foraging adapter are padding and must not trigger API calls. Use SDK result `decisions` for real choice counts, not nominal `rounds`.

## Cases and predictions

| paper_id | Source | Retained world | Fresh choice and conditions | Behavior check |
|---|---|---|---|---|
| `nc_repeated_games` | [Su et al., NC 17:490](https://www.nature.com/articles/s41467-025-67178-6), DOI10.1038/s41467-025-67178-6 | Simultaneous prisoner’s-dilemma payoff matrix, fixed partners, private bilateral history and cumulative points | Both people choose C/D; prior CC/CD/DD incident, four parallel pairs, 12 new interactions, seeds7/11 | Late mutual cooperation and conflict recovery; does not assume Jev inherits the original trained strategy |
| `nc_social_rewarding` | [Pal & Hilbe, NC 13:5928](https://www.nature.com/articles/s41467-022-33551-y), DOI10.1038/s41467-022-33551-y | Author’s 16 two-stage donor/reward policies, well-mixed expected payoff matrices, cooperation accounting, balanced random initial traits | Each member chooses keep/adopt after observing a candidate’s policy and counterfactual payoff; information λ0/.5/1; 16 members, six synchronous sweeps, seeds7/11 | High-vs-low information difference in cooperation **and** social-rewarding share; both differences must be positive for the directional check |
| `nc_collective_foraging` | [Wu et al., NC16:3539](https://www.nature.com/articles/s41467-025-58365-6), DOI10.1038/s41467-025-58365-6 | Actual author State/AgentView and original movement/mining/depletion/visibility loop on two published maps | Jev chooses every goal cell; smooth/random resources × explicit social cues on/off, four people, 120 physical steps, seeds7/11 | Difference in cue benefit between smooth and random maps; reports total rewards and discovery counts |

The repeated-game worlds require 576 fresh choices; rewarding worlds require 576; foraging choices are event-dependent. The safe foraging SDK horizon is 480 per world, but most rounds are empty after physical completion. Every nonempty question is a new behavioral choice. No choice is sampled from the native author policy.

## Evidence limits

These are **paper-derived behavioral reruns with a substituted decision process**, not exact reproduction of the original author trajectories. The repeated-game task replaces learned strategies and does not retrain MARL. The rewarding task replaces Fermi imitation and makes revisions synchronous for batching; original simulations updated one focal person asynchronously. Its rare novel-policy proposals are randomly offered, and the engine still chooses whether to adopt. The offered payoff is computed against the actual other members, including correct self-exclusion for previously absent policies.

Foraging retains the author physical loop but restricts the action menu to at most24 cells:12 nearest and12 spread across remaining unrevealed coordinates. The shortlist uses only coordinate distances and the author’s revealed-cell mask. Hidden reward values, author GP logits, original policy weights, source actions, and paper predictions are never sent to Jev. The cue-off condition removes explicit other-agent positions/directions/recent success, while visible reward observations and the original depletion mask remain; it is not a fully isolated solo condition.

Only two seeds per condition and short horizons are planned. A positive direction would be a pilot mechanism result, not evidence of stationary convergence, quantitative agreement with human data, superior accuracy, or universal Jev fidelity. The social-cue interaction is a test derived from the original paper’s contextual social-learning mechanism, not an assertion that a raw Jev policy matches the paper’s fitted selective policy.

The frozen source hashes and license provenance remain in the existing cookbook adapters: repeated games `examples/nc_evolutionary_games`, rewarding `examples/nc_additional_games`, and foraging `examples/nc_social_sweep/foraging_sources.py`. Existing source files were not changed. Foraging requires the already pinned local source cache `.buildtmp/nc-foraging-source` and its numerical dependencies; `build_cases()` performs no download.

## Offline verification (no model evidence)

`python -m unittest discover -s tests -p test_jev_nc.py -v`

Tests use declared scripted engines only to verify feedback, simultaneous updates, counterfactual payoff accounting, private observations, absence of native action calls, source-world completion, and analysis that can report failure. They do not constitute live Jev runs. The parent runner is responsible for API model identity, fresh-request evidence, batching, retries, costs, events, and the resulting empirical report.
