# Fresh Jev decisions on three NCS social simulation mechanisms

This suite tests external decision-model substitutions, using substantive choices that change the next state. It does **not** count previously checked native-kernel controller steps as Jev judgments. All references below are original research Articles in *Nature Computational Science*. Sources, adaptations and comparison criteria are fixed before provider calls. The common runner owns API access, receipts, spend limits and exact-input replay; this package never reads a credential or calls a provider.

## Cases and claim boundaries

| Article and source | Retained feedback and Jev choice | Declared differences and interpretation |
|---|---|---|
| [Emergence of urban growth patterns from human mobility behavior](https://www.nature.com/articles/s43588-021-00160-6), 2021; [MIT author code](https://github.com/tsinghua-fib-lab/Collective-Mobility-Model), pinned commit `21be090028a0b090c6d32675b73ef821893dfaf9` | Jev selects each resident's destination. The environment freezes last-period population during synchronous choices, then updates positions, population and personal visit histories. | 16 residents, 12×12 torus, six sampled candidates, ten periods; replaces original exploration/return/gravity sampling. Visible vs hidden personal history is an **information ablation**, not removal of latent visited sites: the same balanced candidate proposal uses visits in both conditions. Not the paper's 30,000-person urban-scaling validation. |
| [The effect of co-location on human communication networks](https://www.nature.com/articles/s43588-022-00296-z), 2022; [MIT author capsule](https://doi.org/10.24433/CO.5754680.v1), commit `cbb02661a19d73136dc585645f6f2422054b15a7` | Public 200-node demo, original eligible pairs, office distances, department-pair indicators and initial histories. Sixteen rotating nonisolated researchers choose a contact or no contact each day. Graph, history, five-workday recurrence and lagged shared-contact closure feed subsequent choices. Remote intervention sets pair distance to 2,000 then restores source distances. | 4 baseline, 4 intervention and 4 return days. Replaces the author's coupled global 50+20 draws without replacement with per-person choices; closure is lagged, not within-day second-stage. No-contact is new. It tests a communication-choice transfer on public organizational data, not the original exact protocol or MIT empirical estimates. |
| [Structure-coefficient theorem for evolutionary games on dynamic networks](https://www.nature.com/articles/s43588-026-01068-9), 2026; [MIT author release v1.0.0](https://doi.org/10.5281/zenodo.22152088) | Donation matrix `[[3,-1],[4,0]]`, one uniformly random focal death, a parent among its current neighbors, copied strategy, mutation, then exogenous Markov network transition. Jev replaces **only which eligible neighbor supplies the copied strategy**. Payoff is recomputed from current states and topology. | Six-member ring, star or ring↔star; mutation .01, switching q=1/60; 100 iterations. Selection .1 is a strong-selection setting supported by the article, rather than demo .002. Python port, not bitwise Julia. Short-run means include initialization and are not stationary estimates or a reproduction of the theorem. Single-neighbor events advance automatically without a model request. |

There are 14 worlds across seeds 7/11: four city cases, four co-location cases and six dynamic-game cases. At most 2,008 external choices; deterministic degree-one events reduce the actual count. The actual number comes from provider receipts and SDK decision logs. Each dynamic-game iteration is one focal replacement event, not six independent agent decisions.

The sources are already cached under `.buildtmp/ncs-mobility-native`, `.buildtmp/ncs-colocation-source` and `.buildtmp/ncs-dynamic-games`. CMM raw Git blob SHA and the dynamic release MD5 are checked on construction; co-location checks the pinned clean Git checkout and uses its existing restricted loader. The dynamic archive MD5 is `15d12d6f02aea003e4d37985059a9a31`; original `Simulation.jl` was inspected to preserve death/birth/mutation/network ordering. Its large-scale figure-generation workflows were not released. No upstream code is relicensed or represented as newly authored by ORDO.

## Baselines and outcomes fixed before Jev calls

The baseline uses original mechanisms **on the declared transferred environments**, and is free. CMM uses `rho0=1e-12`, `alpha=-2.55`, `gamma=.21` on the sampled destination menu; hidden-history mode is exploration-only. Co-location applies original periodicity/department/history/closure interaction weights to its per-person menu and adds declared no-contact weight 2,000. Dynamic games use `exp(.1 * payoff)` neighbor parent weights. These baselines do not establish equivalence between a reduced protocol and the complete published model.

The comparison reports all seed-specific outcomes, including null or opposite signs:

- City: last-three-period revisit rate, concentration and occupied sites. Visible-history minus hidden-history revisit rate is the fixed descriptive contrast. The speculative positive direction belongs to this framework's **history-visibility transfer hypothesis**, not the source paper's finding or an acceptance criterion. Before Jev calls, free-rule differences were already negative for both seeds (−0.292/−0.417): the small sampled menu cannot validate the original macro conclusions. We retained this design rather than searching for a favorable contrast.
- Co-location: per-phase contacts, new ties, cross-department ties and local bridges. Remote minus continuous intervention bridge count is the descriptive contrast; a decline is a hypothesis to inspect, not an imposed target.
- Dynamic game: short-run mean cooperation, focal changes and network transitions; switching minus mean of the two fixed-topology means. **No expected sign is registered for this ring/star example.** The paper finds that most dynamic networks do not promote prosocial behavior, and its particular dynamic core-periphery class is different from this minimal demo.

The external public runner uses SDK seed `20261030` and namespaced question/actor IDs. Rule baselines use case seeds and local IDs: they are **independent sampled trajectories**, not matched common random numbers. Rule/model difference is not accuracy against people. Two seeds and short runs cannot establish a general causal or stationary effect. Rule weights, source answers and desired aggregate outcomes never appear in Jev questions.

## Use

Install the project's cookbook dependencies in the selected Python environment (`networkx`, `numpy`). Local existing dependency caches can be selected with `PYTHONPATH=.deps;.buildtmp/behavior-plot-deps;.buildtmp/nc-social-deps` in PowerShell.

```powershell
python -m examples.jev_validation.run --group ncs --preview
python -m unittest discover -s tests -p test_jev_ncs.py -v
```

Actual model calls are performed only by the authorized parent runner. `suite.build_cases()` returns the agreed environment/round/seed metadata; `suite.analyze(results)` computes all contrasts and fresh free-rule comparisons. `Protocol.start/check/finish` verifies the prepare/commit order and rejects invalid batches before world changes. The tests check candidate validity, population conservation, substantive available alternatives, atomic invalid commits and copying only an actual neighbor's strategy.

A successful execution proves that these transferred models can be driven by the external provider and audited/replayed. It alone does not prove a published phenomenon was reproduced. That conclusion depends on the reported contrasts and the stated scope; the original empirical data, theorem and full-scale benchmarks are separate evidence.

**Three paper-derived models integrated and run with Jev does not mean three papers' core results successfully reproduced.** This round is coverage and limitation reporting. More complete source-matched validation is subsequent work.
