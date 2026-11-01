# Source scope and protocol audits

This directory records candidate screening and source-protocol audits for interacting LLM-agent simulations. The featured cases retain convention formation, majority coordination, repeated games and network polarization. Each method page states the selected population, actions, information, update timing, source files and execution scope.

Conventional ABM adapters and early reduced pilots remain available as engineering records. They are not added to the count of original LLM-driven source papers. Current results and portable evidence are indexed in the [cookbook](../cookbook/README.md).

## Configuration and execution

| Source study | Originally LLM-driven? | Actual completion | Evidence assessment |
| --- | --- | --- | --- |
| Ashery et al., Science Advances, Convention formation | Yes: naming choices from personal interaction histories | Earlier pilot: 8/8 spontaneous successes plus minority effects; source repetition and uncapped horizon differ. | Retained as a qualitative pilot with its declared scope |
| De Marzo et al., Science Advances: group coordination | Yes: individual choice after observing others' opinions | N=50, m0=0, 20 worlds and t≤10: 6,279 new Jev choices, 16/20 consensus, mean final coordination .952. | Qualitative coordination in the selected condition; full source models and scaling study remain separate |
| Akata et al., Nature Human Behaviour: repeated games | Yes: GPT-4 choices from round-by-round payoffs and history | Categorical sampling restored for SI B.2: 8×8 pairs, 20 rounds each, 320 fresh choices, 81 cooperative (25.31%). | Historical argmax cooperation: 0%; fresh sampling: 25.31%; archived GPT-4: 63.75%. Feedback and replay pass. [Results](nhb_sampled_results.md). |
| Yang & Chiou, Water Resources Research, Household flood adaptation | Yes: Gemma3 drives multiyear decisions for 100 households | Source, 100 households × 10 years × 50 repetitions and candidate interface audited; no Jev call | Original population should remain fixed. SI Table S5 describes the attributes, but attachment access is incomplete; the population-resampling V1 is not launched. |
| Piao et al., Nature Communications, Network polarization | Yes: newly generated posts/reasons feed subsequent interactions | New Jev + DeepSeek V4.1 Flash 1017 low-reasoning hybrid: 1,000 members, 40 planned epochs; source replay separate. | The recorded hybrid run completes 11/40 epochs, using source epoch-0 networks and opinions and freshly generated later content and choices. [Methods](../nc_polarization_live/README.md). |

## Sources and records

- [Nature Communications and Nature Computational Science landscape](nc_ncs_landscape.md)
- [Repeated games: raw-probability sampling results](nhb_sampled_results.md)
- [Network polarization with Jev and conditional DeepSeek content](../nc_polarization_live/README.md)
- [Science Advances source-protocol audit](sa_original.md)
- [Majority coordination: complete twenty-world N=50 condition](demarzo_results.md)
- [Verification report (JSON)](../appendix_ordo_v2_evidence/majority/verification.json)
- [Repeated games: the source SI B.2 tournament](nhb_original.md)
- [Repeated games: historical argmax arm](nhb_results.md)
- [Completed source-condition run inventory (JSON)](completed_original_runs.json)
- [Supporting-information audit for the water-resource case](wrr_si_audit.md)
- Stopped-run record: `../../runs/stop-misscoped-native-20261030.json` (local run artifact)
- [Featured LLM social simulations](../cookbook/featured_jev.md)
