# Fresh Jev pilots in three Science Advances interaction protocols

This suite supplies environments to the shared live-validation runner. It does not read credentials or call a model itself. `examples.jev_sa.suite.build_cases()` returns 16 fresh cases with isolated state. Under the fixed seeds they jointly require at most **3,021 individual decisions**: 1,021 naming choices (minority members are fixed), 560 majority updates and 1,440 possible public-goods comparisons. Actual public-goods calls are often fewer because equal-strategy comparisons and absorbed colonies require no model judgment.

The suite is ready for live Jev execution. Local interface tests and the unpaid Fermi comparison do **not** establish that a live Jev run occurred. That evidence comes only from the shared runner's completed manifests and provider usage logs. Existing saved author actions and probability lookup tables are not used as a live engine.

## Paper 1: emergent conventions and committed minorities

Ashery, Aiello & Baronchelli (2025), *Emergent social conventions and collective bias in LLM populations*, **Science Advances 11, eadu9368**. [Official article](https://www.science.org/doi/10.1126/sciadv.adu9368), [author manuscript](https://openaccess.city.ac.uk/id/eprint/35211/1/sciadv.adu9368.pdf), [code/data](https://github.com/Ariel-Flint-Ashery/AI-norms).

Reuse the existing ORDO `NamingGame`: 24 members, Q/M choices, five personal interaction memories, +100 for matching and −50 otherwise. Both members decide before either sees the current result. Neither sees population distributions, a partner's current choice or another member's history. The conditions are spontaneous behavior and established Q histories with four/five members committed to M. The latter start each individual with five Q/Q successes, following the selected published minority protocol. Fixed minority members make no Jev requests.

Each condition has seeds 7 and 19 and 96 pairings (four population rounds). Prespecified outcomes are recent pairwise success, latest personal-choice concentration and adoption of M. The paper reports convention formation and minority-driven changes; the pilot checks whether those phenomena appear under **Jev substitution**, with a much shorter horizon. Two seeds cannot estimate the original critical minority fraction. The two-option spontaneous pilot also does not replicate the paper's full ten-name collective-bias analysis.

## Paper 2: majority influence and endogenous coordination

De Marzo, Castellano & Garcia (2026), *AI agents can coordinate via majority-following beyond human scale*, **Science Advances 12, eaea6091**. [Official article](https://www.science.org/doi/10.1126/sciadv.aea6091), [archived full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC13475478/), [author code/data](https://github.com/giordano-demarzo/LLMs-Opinion-Dynamics).

Reuse ORDO `MajorityOpinion` at N=20 and 50, two seeds, four population rounds. Each asynchronous update selects one random individual, who sees only the current opinions of all other members, with freshly randomized aliases, list order and label mapping. No memory, payoff, their own preceding opinion, majority-following instruction or consensus objective is included. Later inputs reflect realized earlier choices, so the simulation is a feedback process rather than disconnected judgment questions.

The paper reports model-dependent majority attraction, consensus times and upper scales for reliable coordination. We report coordination trajectories and first consensus, treating unfinished trajectories as censored at the short horizon. These pilots cannot estimate Jev's critical population size or claim coordination beyond human scale. New Jev inference is used at every queried update; reference response curves are not reused.

## Paper 3: public goods on structured populations

Wang & Su (2026), *Public goods games on any population structure*, **Science Advances 12, eaeb1263**. [Official article](https://www.science.org/doi/10.1126/sciadv.aeb1263), [full primary text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965315/), [author Python/Matlab source](https://github.com/ChaoqianSCI/Spatial-PGGs-any-network), [archived release](https://doi.org/10.5281/zenodo.18060514).

The source was inspected at commit `5a2f280bf76fe3ca36566242ca4edf5700d66229`; `pgggraph_PC.py` Git blob is `a0fba5d7b7dce9615d491c52fd28d8fac6aa3a6c`. Its repository does not expose a standalone license, so its executable source is **not redistributed** here. The adapter independently implements the paper's published payoff equations and update protocol. No large original Numba job, Matlab solver or training is launched.

Every member organizes one group containing themselves and their neighbors. Individuals also participate in groups organized by their neighbors. Contributors pay c=1 in each game; total group contributions are multiplied by r and divided equally. Actual payoff is the **average** across the focal individual's participating groups (paper Eq. 6).

The paper's pairwise-comparison rule (Eq. 2) selects a random focal individual and random neighbor. When their strategies differ, the focal individual keeps their own strategy or adopts the neighbor's; the original probability is a weak-selection Fermi function with δ=.01. **Our fresh run substitutes Jev's judgment for this probability** while retaining the coupled payoff environment, legal keep/adopt actions, one initial random cooperator, asynchronous feedback and homogeneous absorbing states. Jev sees only public game rules and the focal/selected-neighbor strategies and observed average payoffs. It is not given the Fermi formula, threshold result or strategy answer.

Conditions are N=10 star with r=3, star with r=6 and complete network with r=6, each with seeds 7 and 19. Each case contains four disjoint independent colonies and 60 elementary updates per colony (six Monte Carlo steps). One focal opportunity per colony can be batched, while successive updates within a colony remain sequential.

Under the **original** evolutionary mechanism, the paper identifies stars as favorable for public-goods cooperation above a synergy threshold, while complete networks do not support cooperation through the same comparison mechanism. The selected star demonstration has finite threshold about 4.64; r=3/6 bracket it. We compare final fractions and absorption across these conditions. Jev does not inherit the paper's theorem: altered judgments may preserve or reverse the direction. Four colonies and two seeds cannot estimate the paper's fixation probabilities, which originally required 10⁶–10⁹ independent simulations and up to 4×10⁵ full Monte Carlo steps. This case establishes an auditable **decision-kernel substitution experiment**, not exact reproduction of a weak-selection result.

## Interfaces, tests and evidence

The shared runner consumes [suite.py](../../examples/jev_sa/suite.py); each case exposes an independent SDK environment with `describe`, `prepare` and `advance`. `analyze(results)` accepts case metadata plus complete SDK manifests and returns observed outcomes alongside original-paper expectations. Private local memories and strategy states are stored as metrics for audit and are not injected into other agents' observations.

```powershell
python -m unittest discover -s tests -p test_jev_sa.py -v
```

Five focused unpaid tests cover source coverage, independently allocated cases, the overlapping-group payoff equation, fixed-member and hidden-current-choice boundaries, absorption, and an actual feedback trajectory with the original Fermi comparator. These validate local mechanics and the interface; they do not validate live Jev behavior or human fidelity.
