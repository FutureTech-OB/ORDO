# Published LLM social simulations through ORDO

These examples implement published population-interaction protocols through the public Environment/DecisionEngine SDK. The environment owns visible information, interaction, memory, rewards, and state updates; the engine supplies each current choice.

## Recorded executions

The 29 October behavioral pilot contains 36 Jev worlds and 36 uniform-rule controls with 32,457 fresh Jev choices. All eight spontaneous-convention worlds meet the criterion. Committed minorities change ordinary-member adoption; opinion consensus counts are 3/3, 10/10, and 2/3 at N=10, 50, and 100. The later twenty-world N=50 majority condition is documented separately in the main appendix.

Archive verification reconstructs 39 author convention runs and checks imported aggregate opinion trajectories and probability reference tables. A subsequent OpenRouter connectivity trial contains 18 fresh decisions, 12 requests, and $0.000348852 in reported usage.

The organizational extension adds positions, reporting contacts, and departmental memory permissions to a thousand-member convention process. It uses disjoint synchronous pairs within periods.

## Execute and customize

The commands below run fresh model experiments or author-archive replay. Set OPENROUTER_API_KEY for paid inference; choose a new output directory. Source downloads are pinned and checked. Restricted archive readers load the specified data members without constructing arbitrary pickle objects. Full runtime caches remain local.

NamingGame and MajorityOpinion implement describe, prepare, and advance. One naming SDK step is one pair interaction; one opinion SDK step is one individual update. Independent choices in a pair may be batched before settlement. Asynchronous opinion updates retain their causal order; independent worlds can share provider batches.

Each run records source manifests, events, results, state checks, opinion segments, and interface records. The archive stage verifies transitions conditional on recorded choices. Fresh behavioral runs use new judgments and record engine, sampling, and protocol adaptations.

## Configuration and execution

| Case | Source study | Recorded evidence |
| --- | --- | --- |
| [Conventions, collective bias and committed minorities](conventions.md) | Ashery, Aiello & Baronchelli, Science Advances (2025) | 39 archived author LLM experiments replayed with identical states and records; offline engine-interface checks |
| [Majority influence and coordination](majority.md) | De Marzo, Castellano & Garcia, Science Advances (2026) | Trajectory and reference-probability import with integrity checks; offline asynchronous-opinion and engine-interface verification. |

```bash
python -m examples.llm_abm_cookbook.replicate_behavior --allow-paid --max-cost-usd 2 --max-requests 6000 --output runs/behavior
python tools/analyze_behavior_replication.py --run runs/behavior
```

```bash
python -m examples.llm_abm_cookbook.run --download --output runs/llm-abm-replay
python tools/export_llm_abm_verification.py --run runs/llm-abm-replay
python -m unittest discover -s tests -p test_llm_abm_cookbook.py -v
```

```python
from orgabm.sdk import FunctionEngine, run_simulation
from examples.llm_abm_cookbook.environments import NamingGame

# Uniform-choice control for execution-path verification:
world = NamingGame(agents=24, options=list('QMXYFJPRCD'), memory_size=5, seed=7)
uniform = FunctionEngine(lambda state, q: {a: 1 / len(q['criteria']) for a in q['criteria']},
                         name='explicit-uniform-control')
result = run_simulation(world, uniform, rounds=240, seed=7)
```

## Sources and records

- [Convention formation and committed minorities: results](behavior_results/README.md)
- [Conventions, positions, and publishing permissions in a large organization](../organizational_conventions/README.md)
- [Convention formation, collective bias, and committed minorities](conventions.md)
- [Majority influence and population coordination](majority.md)
- [Archived LLM-simulation verification](verified_results.md)
- [Verification report (JSON)](verification.json)
- [Historical OpenRouter decision trial](openrouter_live_trial.md)
- [Fresh Jev behavioral pilot: protocol](behavior_protocol.md)
- [LLM social simulation environments](../../examples/llm_abm_cookbook/environments.py)
- [run_simulation](../../orgabm/sdk.py)
