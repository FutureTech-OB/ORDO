# Cookbook catalog

The catalog links five organizational recipes to their plans and evidence. Plans describe populations, structure, tasks, policy factors, seeds and engine selection. Preview expands the parameter grid and estimates questions before execution. The JSON catalog is also available to interfaces and research assistants.

The featured social-simulation entry follows published LLM-driven interaction protocols. Conventional rule-model portability remains a separate collection.

## Configuration and execution

| Demonstrated capability | Inspectable example |
| --- | --- |
| Reproduce existing ABM studies | Science Advances convention and coordination records with fresh Jev qualitative runs; NC repeated-game trajectories and further native-kernel checks below. |
| Extend to organizational research | Extends conventions to 1,000-member organizations with positions, reporting contacts, departmental readers and publishing grants; templates expose authority, resources and information. |
| Conventional ABM support | Original strategies, C/C++ kernels or Mesa rules run through ORDO scheduling, execution, recording and reference checks. |

| Case | Source | Completed execution and evidence scope | Entry point |
| --- | --- | --- | --- |
| Conventions and committed minorities | Science Advances, 2025 | 39 author runs, 12,449 pairs and 22,622 nonfixed-member choices replayed; fresh Jev behavior recorded separately | [Methods and results](../llm_abm_cookbook/README.md) |
| Majority influence and coordination | Science Advances, 2026 | Public trajectories and probability tables checked; fresh Jev N=10/50/100 pilots retain all worlds | [Fresh run](../llm_abm_cookbook/behavior_results/README.md) |
| Organizational social learning | Nature Communications, 2016 | Existing Python adaptation with independent reference; separate from original R execution and full source figures | [Conventional ABM adapters](../abm_cookbook/README.md) |
| Repeated games and strategy evolution | Nature Communications, 2026 | 972 matches and 12 populations of 64; 77,280 native choices; archived strategies and generation loops checked without Q-table retraining | [Case](../nc_evolutionary_games/README.md) |
| Reputation, social rewards and cooperation | Nature Communications, 2022 | 18 worlds of 100 members and 3,000 updates; 54,000 native choices, matching complete states and cooperation each update. | [Case](../nc_additional_games/README.md) |
| Social pressure and propagation cascades | Nature Communications, 2022 | 27 worlds of 128–1,024 members, 14,976 native activation choices; source C kernel matches layer by layer | [Case](../nc_social_sweep/README.md) |
| Collective foraging and social learning | Nature Communications, 2025 | 18 worlds of four members and 400 steps; 2,096 target choices on two source maps. States, private observations, navigation and collection match the source. | [Case](../nc_social_sweep/foraging.md) |
| Collective mobility and urban growth | Nature Computational Science, 2021 | 15 worlds with 128/1,000 members and 181,440 native updates; period-level C++ checks. The 600 SDK actions control whole periods. | [Case](../ncs_mobility/README.md) |
| LLM Network polarization | Nature Communications, 2026 | 123 snapshots of 1,000 members, 491,474 contact rows and 120,000 archived state assignments across three topics; zero new model judgments. | [Case](../nc_polarization/README.md) |

| Item | Completed items | Entry point |
| --- | --- | --- |
| Organizational extension of conventions | 12 Jev and 36 rule worlds of 1,000 members, over 32 periods; 92,058 fresh choices comparing positions and guidance | [Case](../organizational_conventions/README.md) |
| Organizational mechanism templates | Knowledge sharing, approval bottlenecks, memory permissions, Persona placement and scale: 50 free-rule worlds plus three population jobs. | [Organization cookbook](README.md) |
| Conventional Mesa reference | Wealth, spatial cooperation, Schelling and organizational learning: 33 worlds, 645 rounds, native rules checked against declared references | [Case](../abm_cookbook/README.md) |

```bash
python -m pip install -e ".[mesa,harness,cookbooks]"
python -m examples.research_cookbook.run --list
python -m examples.research_cookbook.run --recipe nc-evolutionary-games --preview
python -m examples.research_cookbook.run --recipe nc-evolutionary-games --output runs/my-games-suite
```

```bash
python -m examples.research_cookbook.run --recipe all --download --output runs/my-free-cookbook-suite
```

```bash
python tools/verify_research_cookbook.py
```

## Sources and records

- [Featured LLM social simulations](featured_jev.md)
- [Cookbook coverage verification (JSON)](coverage_verification.json)
- [Published LLM social simulations through ORDO](../llm_abm_cookbook/README.md)
- [Convention formation and committed minorities: results](../llm_abm_cookbook/behavior_results/README.md)
- [Conventional ABM portability cookbook](../abm_cookbook/README.md)
- [Case](../nc_evolutionary_games/README.md)
- [Case](../nc_additional_games/README.md)
- [Case](../nc_social_sweep/README.md)
- [Case](../nc_social_sweep/foraging.md)
- [Case](../ncs_mobility/README.md)
- [Case](../nc_polarization/README.md)
- [Case](../organizational_conventions/README.md)
- [Organizational experiment cookbook](README.md)
- [Machine-readable experiment catalog](../../examples/research_cookbook/catalog.json)
