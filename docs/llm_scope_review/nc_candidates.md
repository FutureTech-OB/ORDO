# Nature Communications candidate review

Screening distinguishes original LLM-agent simulations from classical evolutionary models, empirical network analysis and static inference. The candidate sources and adaptation records are retained below. Piao et al.'s network-polarization model is the featured large-population LLM case, with agent opinions, generated communication and changing social ties.

Other NC adapters exercise compatible interaction environments and source kernels. Their results remain separate from replications of an originally LLM-driven model.

## Configuration and execution

| Source study | Interaction and source LLM function | Original scale and source audit | Full Jev choice substitution |
|---|---|---|---|
| Piao et al., Nature Communications (2026), [Emergence of polarization in networks of large language model agents](https://www.nature.com/articles/s41467-026-78228-y), DOI 10.1038/s41467-026-78228-y | Members receive posts, update stance and reasons, generate persuasive posts, and choose ties. New content feeds subsequent agents. | Main figure: N=1,000, 40 epochs, GPT-3.5-Turbo, temperature=1. [Pinned repository](https://github.com/tsinghua-fib-lab/LLM_for_Polarization/tree/7bc447f6d470aa232f93de5dabaa4c87fc4414d9). Default run.py instead loads N=2,000 and 2,000 epochs. Repetition and strict token caps are not fully specified. | Discrete stance and tie choices can use Jev; newly generated reasons and persuasive posts require a content engine and feed subsequent interactions. |
| [Disentangling interaction and bias effects in opinion dynamics of large language models](https://www.nature.com/articles/s41467-026-77340-3), *Nature Communications* (2026), DOI 10.1038/s41467-026-77340-3 | Two LLM agents debate; a separate five-point stance query measures opinions | [Repository](https://github.com/Priesemann-Group/llm_opinion_dynamics): two agents, five discussion rounds, 12 topics, 5×5 initial-state combinations and six models. The 25 combinations are not repetitions. | Free arguments carry the interaction. Replacing stance measurement alone changes the measurement layer; a complete hybrid requires a content-generation module. |

| Source | Audit conclusion |
|---|---|
| [Yang & Chiou WRR 2026](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2025WR042111), DOI 10.1029/2025WR042111 | 100 households with multiyear flood, adaptation and trust feedback. Gemma3:4b selects among three or four actions; generated reasons do not feed back. BSD-3-Clause source environment. See [audit](wrr_original.md). |
| [Strategic behavior of large language models and the role of game structure versus contextual framing](https://www.nature.com/articles/s41598-024-69032-z), *Scientific Reports* (2024), DOI 10.1038/s41598-024-69032-z | Excluded from interacting-ABM cases: one-shot choice sampling without repeated endogenous environmental feedback. Repeated games are future work in the source. |
| [Group size effects and collective misalignment in LLM multi-agent systems](https://doi.org/10.1073/pnas.2531697123), PNAS 123(34), e2531697123 (2026); [source repository](https://github.com/Ariel-Flint-Ashery/LLM-group-size/tree/ddbbca5b7fd0551ed409903c275f75505db7da9d) | LLM coordination with precomputed H=5 state-conditioned probability tables reused at population scale. History contains actions and payoffs. This source table simulation differs from fresh per-agent, per-event inference. |
| [Large language models instantiate evolutionarily robust strategies of cooperation](https://academic.oup.com/pnasnexus/article/5/6/pgag210/8705778), *PNAS Nexus* (2026), DOI 10.1093/pnasnexus/pgag210; [repo](https://github.com/Saptarshi07/LLM-strategy) | Includes a 10-round two-LLM PD (R=3,S=0,T=5,P=1), static inference and fixed-strategy tournaments. actual-play.py overwrites a new action with undefined p2moves[round-1]; API placeholders also need repair. No fresh run was made. |

## Sources and records

- [Network polarization with Jev and conditional DeepSeek content](../nc_polarization_live/README.md)
- [Nature Communications and Nature Computational Science landscape](nc_ncs_landscape.md)
- [Emergence of polarization in networks of large language model agents](https://www.nature.com/articles/s41467-026-78228-y)
- [Source repository](https://github.com/tsinghua-fib-lab/LLM_for_Polarization/tree/7bc447f6d470aa232f93de5dabaa4c87fc4414d9)
- [Disentangling interaction and bias effects in opinion dynamics of large language models](https://www.nature.com/articles/s41467-026-77340-3)
- [Source repository](https://github.com/Priesemann-Group/llm_opinion_dynamics)
- [Yang & Chiou WRR 2026](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2025WR042111)
- [Water Resources Research source audit](wrr_original.md)
- [Strategic behavior of large language models and the role of game structure versus contextual framing](https://www.nature.com/articles/s41598-024-69032-z)
- [Group size effects and collective misalignment in LLM multi-agent systems](https://doi.org/10.1073/pnas.2531697123)
- [Source repository](https://github.com/Ariel-Flint-Ashery/LLM-group-size/tree/ddbbca5b7fd0551ed409903c275f75505db7da9d)
- [Large language models instantiate evolutionarily robust strategies of cooperation](https://academic.oup.com/pnasnexus/article/5/6/pgag210/8705778)
- [repo](https://github.com/Saptarshi07/LLM-strategy)
