# Technical appendix: organizational social-learning prototype

## Scope and provenance

The environment adapts Barkoczi & Galesic (2016), *Social learning strategies modify the effect of network structure on group performance*, Nature Communications 7:13109, https://doi.org/10.1038/ncomms13109. The reviewed author repository is pinned to `93b5f6fb18290ff67a5a676c9ef98a5aa3165f71`. The original R code was inspected, not executed in this project. Python random streams and the added action, policy and organizational interfaces differ from the original study.

## Environment and transitions

Each employee holds a 15-bit work process. NK complexity is 7; each component uses itself plus seven sampled dimensions. As in the inspected generator, the sampled dimensions can include itself. Component contributions are rounded to one decimal place, averaged, normalized by the maximum, then transformed by `100 * normalized**8`. Initial processes are sampled without replacement. Every employee starts with zero cumulative earnings.

Employees choose keep, explore, or copy one of three observed coworkers. Exploration flips one random bit. A process is retained only if it strictly improves performance. A non-improving experiment incurs the active failure penalty. Copied solutions additionally require an improvement at least as large as the active approval threshold. Denied copy requests preserve the current process and incur no additional fee. Gross performance and net earnings are reported separately.

All observations refer to the round-start snapshot. Decisions are completed before any process is updated. Mutation proposals and action draws use event-keyed seeds. The three most recent private outcomes become visible in the next round. No untested payoff, global optimum or other agent's private history enters an employee record.

## Organization modules

Department membership is balanced, shuffled with an independent seed stream, and held constant. Contact modes are: uniform organizational sampling without replacement; three coworkers in the same department; two in the same department plus one outside. If only one department exists, the bridge mode falls back to organization-wide sampling. Each department must have at least four employees. Contacts are sampled per round, rather than being a persistent friendship graph.

Anonymous mode removes department labels from decision records while retaining the same contacts and observations. Management guidance is a fixed advisory instruction. It does not set an exploration probability. The approval threshold is a mechanical governance constraint, not a manager agent or learned policy. Guidance, failure charges and approval rules activate at the configured round; contact mode and anonymity apply from the first round.

Rule engines operate on the same three-decimal observed scores as decision models. Best-member chooses uniformly among equally high-scoring visible peers when their score exceeds the employee's; otherwise it explores. Conformity chooses a modal process (uniformly among modal processes), copying it only if it improves observed performance. If all sampled process frequencies tie across multiple processes, it explores. These implementation details and rounding must be kept fixed when comparing engines. They are not a claim of exact original-model replication.

## Model interface, batching and randomness

Jev is version pinned to `jev-1.14.0`. The public rules occupy shared state; each employee observation occupies its own choice question. Option presentation order is randomized deterministically. Batches contain independent questions in the same round. They may execute concurrently, but no future round is queried before current actions have changed the state. No cached probabilities cross agents or events.

The five returned action probabilities are checked for keys, finite values, nonnegativity and near-unit mass. Raw values are saved; small rounding discrepancies are normalized during sampling. An action draw is independent of response completion order. API probabilities are treated as candidate simulation policies; classification calibration alone does not demonstrate calibrated human choice frequencies.

## Replication and inference

The independent unit is a simulated world. Matched seed comparisons share initial states, environment and exogenous streams. The paths may diverge after treatment. Population size changes alter initial sampling and contacts, so scale comparisons require their own repeated-world design. Monte Carlo repetition describes model variability and does not eliminate systematic model error.

The archived pilot contains four guidance × penalty conditions and three seeds with 1,000 employees and 12 rounds each: 144,000 fresh decisions. Mean exploration effects of guidance were +23.63 percentage points at zero penalty and +14.71 at a 10-point penalty. The interaction was negative in all three seeds. Final-performance gains were unstable and cumulative net earnings were lower under guidance in these short runs. The fixed best-member reference outperformed all Jev conditions on final performance and cumulative net earnings. No population of real workers was used for validation.

The archive retains aggregate trajectories and provenance hashes. Its source audit replayed all 144,000 saved actions and state transitions. The full original request archive is not bundled in this compact repository draft. New command-line experiments save complete action trajectories and live raw responses locally. The original pilot must be packaged for external auditing before submission; aggregate replay alone is not full rerun reproducibility.

## Known limitations and planned comparisons

This release's new organization modules have mechanism tests and rule-based demonstrations; their live Jev effects are not yet measured. Same-environment ordinary LLM, thinking LLM and open decision-model comparisons are pending. API version drift, probability distortion, wording sensitivity, limited time horizons and uncertainty about human validity remain substantive risks. A future evaluation should compare action distributions, dynamic outcomes and intervention contrasts, as well as throughput, cost and independent repetitions affordable at a fixed budget.
