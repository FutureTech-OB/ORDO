# Science Advances source-protocol audit

Ashery et al. study decentralized conventions and committed minorities in a 24-member naming game. The adapter retains pairwise encounters, visible personal history, matching payoffs and fixed-member behavior. The new Jev arm uses four repetitions per spontaneous memory condition, three per minority condition and a 1,000-pair cap. Author-record replay separately reconstructs 39 archived experiments.

De Marzo et al. study majority influence with asynchronous binary opinion updates. The completed source-condition run uses N=50, balanced initialization, 20 independent worlds, rescaled time up to 10 (500 updates) and early consensus stopping. Only the selected member changes at each update. The local observation and action ordering are recorded before a fresh engine judgment.

The majority run contains 6,279 fresh Jev choices and 16 consensus worlds; mean final coordination is 0.952. The dedicated results page compares the archived model distributions. Smaller historical pilots remain separately identified. Source repositories and exact execution commands are preserved below.

## Configuration and execution

| Item | Source paper/Source condition | Fresh Jev complete-condition plan |
| --- | --- | --- |
| Population and initialization | N=50, m₀=0; 25 members per opinion | Fully retained and reinitialized per world |
| Independent worlds | 20 realizations / model | **20 independent worlds**, with 20 presaved seeds |
| Horizon / stopping | dt=1/N; consensus or t=10 | Consensus or **500 asynchronous updates**; no further calls after consensus |
| Visible information | Current opinions of the other N−1 members; own previous opinion hidden | Full list of **49 peers**, without pruning or statistical aggregation |
| Roles / memory / rewards | Homogeneous, without memory or rewards | Retained |
| Names and bias handling | New random names, shuffled lists and random k/z opinion mapping | Regenerate 50 two-character alphanumeric aliases per step, remove self, shuffle 49 peers, and swap action labels with probability 0.5. |
| Feedback and timing | Each member observes the distribution after the preceding update | Retained; batch only independent worlds |
| Prompt | Ask which opinion to support; no instruction to follow the majority or reach consensus | Preserve source counting and list semantics; valid Jev actions remain k/z |
| Source-model sampling | Source LLM T=0.2 with bracketed text output | Jev probability interface with declared sampling; source-model temperature is a separate parameter |
| Inference volume | At most 20×50×10=10,000 individual updates | Same upper bound; consensus worlds stop requesting judgments |

| Source model | Actual file rows | Full-consensus rows | Mean final C | Median C | Interquartile range |
| --- | ---: | ---: | ---: | ---: | --- |
| Claude 3 Haiku | 28 | 0 | 0.2671 | 0.28 | 0.16–0.40 |
| Claude 3 Opus | 21 | 21 | 1.0000 | 1.00 | 1.00–1.00 |
| GPT-3.5 Turbo | 25 | 0 | 0.0864 | 0.08 | 0.04–0.12 |
| GPT-4 Turbo | 25 | 25 | 1.0000 | 1.00 | 1.00–1.00 |
| Llama 3 70B | 20 | 8 | 0.8520 | 0.90 | 0.83–1.00 |

| Item | Source Fig. 2 condition | Historical behavior_results | New short jev_sa pilot | This run: complete selected condition |
| --- | --- | --- | --- | --- |
| N | 50 | 50, with additional 10/100 pilots | 20/50 | 50 |
| N50 Independent worlds | 20 | **10** | **2** | **20** |
| Maximum time | t=10 | t=10 | **t=4** | t=10 |
| Decision engine | Five source generative LLMs | Live Jev | Live Jev | Fresh Jev arm |
| Source prompt / dynamic information | Complete memory-free peer list | Semantic adaptation with full peer list | As above | Source counting and list prompt adapted with explicit differences |
| Declared scope | Source multimodel Fig. 2 | Qualitative engine-substitution pilot with fewer source repetitions | Small, short-horizon pilot | Completion supports the declared N=50, 20-world Jev substitution condition |

| Item | Complete plan |
| --- | --- |
| Population and network | N=24, complete network; random initiator and random neighbor |
| Name pool | W=10, Q/M/X/Y/F/J/P/R/C/D |
| Memory | Last H=5 own/opponent actions and payoffs, window cumulative score, and locally renumbered rounds. |
| Initial state | Empty histories throughout initialization; no central convention or committed minority |
| Payoff | Matching actions: +100 each; mismatch: −50 each |
| Information and timing | Population size and others' histories are hidden. Paired members decide independently before settlement and memory updates. |
| Action order | Reshuffled for each individual at every interaction |
| Repetitions | **40 independent worlds**, following the Fig. 1 caption |
| Source stopping rule | Last 3N=72 pairs all match; source population() has no fixed 1,000-pair cap |
| Budget stop | Original-event recovery is supported. Budget limits preserve actual completion status and do not define a scientific stopping criterion. |

| Item | Source Fig. 1 / Fig. 3 | Historical behavior_results | New short jev_sa pilot |
| --- | --- | --- | --- |
| Spontaneous main condition | N24/H5/W10 | Same parameters, plus W2 | W2 |
| Spontaneous repetitions | 40 in main-figure caption | **per condition4** | **per condition2** |
| Spontaneous stopping | Last 72 pairs all match, with no 1,000-pair cap | Adds a **1,000-pair cap** and **≥95% same-name actions** criterion | Fixed **96 pairs** |
| Minority horizon | Source committed() uses exactly 1,000 pairs | 1000 events | **96 events** |
| Minority direction | Both directions | **only Q→M** | **only Q→M** |
| Minority repetitions / criterion | SI memory length 10/3 by model; figure criterion: 95% recent matching | **3 per condition**; ordinary-member target-action share also ≥95% | **2 per condition**; latest choices and short-window coordination |
| Supported statement | Selected source-condition replication | Exploratory qualitative fresh-Jev behavior | Target not observed in the short horizon; longer-run results are separate |

```powershell
python -m examples.llm_original_sa.run --preview --output runs/llm-original-sa-demarzo-20261030
python -m examples.llm_original_sa.run --allow-paid --max-cost-usd 1 --output runs/llm-original-sa-demarzo-20261030
```

## Sources and records

- [AI agents can coordinate via majority-following beyond human scale — journal article](https://www.science.org/doi/10.1126/sciadv.aea6091)
- [AI agents can coordinate via majority-following beyond human scale — full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC13475478/)
- [Source repository](https://github.com/giordano-demarzo/LLMs-Opinion-Dynamics)
- [Majority coordination: complete twenty-world N=50 condition](demarzo_results.md)
- [Majority-coordination author endpoint data (JSON)](demarzo_author_endpoints.json)
- [Convention formation and committed minorities: results](../llm_abm_cookbook/behavior_results/README.md)
- [Science Advances pilot results](../jev_sa/results.md)
- [Emergent social conventions and collective bias in LLM populations — full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12077490/)
- [Source repository](https://github.com/Ariel-Flint-Ashery/AI-norms)
- [ashery_fig1_plan.json](../../examples/llm_original_sa/ashery_fig1_plan.json)
- [Emergent Social Conventions and Collective Bias in LLM Populations — preprint](https://arxiv.org/html/2410.08948v2)
- [arXiv v3, 2024-12-22, Appendices A–F](https://arxiv.org/html/2409.02822v3)
