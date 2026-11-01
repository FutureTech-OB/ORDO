# Organizational experiment cookbook

These five recipes combine organizational learning, authority and review capacity, information disclosure, Persona placement, and population scale. They use reusable plans, paired seeds and inspectable event records. The recorded local suite contains 50 simulation worlds and three population-construction jobs. Free rules provide a reproducible mechanism baseline; Jev is a replaceable decision engine.

Each recipe includes its question, configuration, execution command and recorded outputs. The featured LLM simulation replications and organizational convention extension have their own entry point.

## Configuration and execution

| Case | Organizational question | Integrated system capabilities | Default run |
| --- | --- | --- | --- |
| [01 Knowledge sharing and adoption rights](01_knowledge_and_authority.md) | Can members adopt good solutions encountered in other departments? | Department boundaries, contacts, institutional constraints and diffusion records | 120 members, 12 worlds |
| [02 Approval bottlenecks and delegation](02_delegation_and_capacity.md) | How do more review capacity and greater delegation affect bottlenecks? | Reporting, staged choices, task dependencies, queues and resource accounts | 12 members, 12 worlds |
| [03 Risk-information disclosure](03_information_disclosure.md) | What changes when only managers know a risk versus employees also knowing? | Department memory, access rights, timed disclosure, custom engines and exposure audits | 12 members, 18 worlds |
| [04 Build an organization from a Persona pool](04_persona_to_organization.md) | Construct position-conditioned populations, then compare institutions using the same members | Persona import, position probabilities, threshold sampling, frozen populations and structure | 3 construction jobs and 4 downstream worlds |
| [05 Scale and engines](05_scale_and_engines.md) | How do decision volume, waiting and log costs change as the same workflow scales? | Multilevel reporting, population generation, stage batching, engine substitution and budget preview | 100/1,000 members, 4 worlds |

| File | Use |
| --- | --- |
| `cookbook-run.json` | Completion, Python version, core/recipe hashes and API-call markers |
| `<recipe>/summary.json`, `summary.csv` | Per-world results; recipe 04 also includes assignments and downstream worlds |
| `<recipe>/condition-means.json` | Condition means; recipe 04 summarizes construction jobs |
| `<recipe>/paired-contrasts.json` | Within-seed contrasts for recipes 01–03; empty for other cases |
| `<recipe>/<condition>/world-*/config.json` | Expanded executed configuration |
| `world-*/events.jsonl`, `result.json` | Inputs, probabilities, actions, transitions and period metrics |
| `world-*/workflow-state.json` | Final task states, balances and returns |
| `world-*/visibility-examples.json` | Selected members' visible memory in rounds 1 and 3 of recipe 03 |

```bash
python -m pip install -e ".[mesa]"
python -m examples.cookbook.run --recipe all --output runs/cookbook-local
```

```bash
python -m examples.cookbook.run --recipe 02 --output runs/cookbook-02
```

```bash
python -m orgabm experiment --plan examples/cookbook/plans/02/delegation_x_capacity/plan.json --preview
python -m orgabm experiment --plan examples/cookbook/plans/02/delegation_x_capacity/plan.json --output runs/my-approval-study
```

```bash
python -m examples.cookbook.run --recipe all --export-only --output runs/my-cookbook-inputs
```

## Sources and records

- [Cookbook catalog](catalog.md)
- [Conventional ABM portability cookbook](../abm_cookbook/README.md)
- [01 Knowledge sharing and adoption rights](01_knowledge_and_authority.md)
- [02 Approval bottlenecks and delegation](02_delegation_and_capacity.md)
- [03 Risk-information disclosure](03_information_disclosure.md)
- [04 Build an organization from a Persona pool](04_persona_to_organization.md)
- [Population scale and interchangeable engines](05_scale_and_engines.md)
- [Recorded organizational cookbook results](verified_results.md)
- [examples/cookbook/plans](../../examples/cookbook/plans)
- [Experiment-plan and research-assistant tool API](../public_api.md#experiment-plan-and-harness-tools)
- [Organizational experiment definitions](../../examples/cookbook/recipes.py)
- [Organizational cookbook execution entry point](../../examples/cookbook/run.py)
- [Organizational cookbook checks](../../tests/test_cookbook.py)
