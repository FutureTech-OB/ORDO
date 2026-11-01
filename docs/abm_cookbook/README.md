# Conventional ABM portability cookbook

Four reference models demonstrate the environment–decision interface: Mesa wealth exchange, spatial cooperation, Schelling segregation, and organizational NK learning. Across 33 worlds, 645 rounds and 80,511 action questions, the declared reference checks match. These runs use original rules and no model API calls. The featured LLM-driven cases are in the separate social-simulation cookbook.

Adapters expose local observations and permitted actions, preserve the source update order, and commit actions through the environment. Each recipe specifies the reference implementation and the state variables checked. Install the cookbook extras before running the commands below.

## Configuration and execution

| Cookbook | Research area and source model | Adapter boundary | Retained environmental mechanisms |
| --- | --- | --- | --- |
| [01 Wealth exchange](01_wealth.md) | Economics: random wealth exchange in a closed economy | Recipient choice for each valid transfer | Random movement, sequential activation, wealth conservation and nonnegative balances |
| [02 Spatial cooperation](02_cooperation.md) | Economics / society: spatial prisoner's dilemma | Cooperate/defect strategy updates | Spatial neighborhoods, payoff matrix, cumulative returns and three activation orders |
| [03 Schelling Residential segregation](03_schelling.md) | Sociology: local preferences and spatial segregation | Stay / move | Source happiness timing, empty-site selection, movement order and agent types |
| [04 Organizational social learning](04_organization.md) | Organization: learning and knowledge diffusion on complex tasks | Keep, explore or copy an observed peer | NK environment, contacts, synchronous updates, institutional thresholds and payoffs |

| File | Content |
| --- | --- |
| `manifest.json`, `summary.csv` | Completion, world results and usage |
| `cases.json`, `preview.json` | Declared cases and decision/request upper bounds |
| `world-*/case.json` | Single-world input |
| `world-*/audit.json` | Reference scope and exact checks |
| `world-*/ordo/events.jsonl`, `result.json` | ORDO decisions, stage order, interventions and metrics |
| `world-*/ordo-states.jsonl` | Complete ORDO member trajectories |
| `world-*/native-reference.json` | Complete independent trajectories for three official models |
| `world-*/reference/` | Independent Python organizational reference records |

```bash
python -m pip install -e ".[mesa]"
python -m examples.abm_cookbook.run --model all --output runs/abm-portability
```

```bash
python -m examples.abm_cookbook.run --model schelling --output runs/schelling-through-ordo
python -m examples.abm_cookbook.run --model cooperation --engine jev --preview
```

```bash
python -m examples.abm_cookbook.run --cases examples/abm_cookbook/jev_smoke_cases.json --preview
```

```bash
python -m examples.abm_cookbook.run --cases examples/abm_cookbook/jev_smoke_cases.json --engine jev --preview
```

## Sources and records

- [Published LLM social simulations through ORDO](../llm_abm_cookbook/README.md)
- [01 Wealth exchange](01_wealth.md)
- [Spatial cooperation](02_cooperation.md)
- [03 Schelling Residential segregation](03_schelling.md)
- [04 Organizational social learning](04_organization.md)
- [Verified conventional-ABM results](verified_results.md)
- [Verification report (JSON)](verification.json)
- [Conventional ABM case configurations](../../examples/abm_cookbook/cases.json)
- [Conventional ABM adapters](../../examples/abm_cookbook/adapters.py)
- [Conventional ABM execution entry point](../../examples/abm_cookbook/run.py)
- [ABM portability checks](../../tests/test_abm_portability.py)
- [Organizational experiment cookbook](../cookbook/README.md)
