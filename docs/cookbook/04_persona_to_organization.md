# From Persona pools to organizational positions

The population builder supports two workflows. Pool assignment scores every candidate–position combination, then samples assignments without replacement using the scores. Streaming assignment draws candidates and accepts them when the model's estimated position probability reaches the threshold, defaulting to 0.5. It reports vacancies when candidates or the evaluation budget are exhausted.

In the recorded synthetic-score checks, full-pool allocation fills all 12 positions using 48 evaluations. Streaming at 0.5 fills them using 20 evaluations; a 0.95 threshold leaves all positions unfilled after 48 evaluations. Each completed population is frozen before comparing delegation settings, producing four downstream worlds. These deterministic test scores exercise allocation and bookkeeping; live position-judgment validity is a separate evaluation.

## Configuration and execution

| Personal background | Synthetic manager-position score | Synthetic employee-position score |
| --- | --- | --- |
| team_lead | 0.90 | 0.35 |
| specialist | 0.20 | 0.85 |

| Mode | Executed process | Intended use |
| --- | --- | --- |
| `pool` | Score all candidates × position types, then sample weighted assignments without replacement | Inspect full candidate pool and scoring evidence |
| `stream` | Draw candidates in random order and accept those meeting the position-probability threshold | Threshold-defined inclusion until quotas or limits |

```bash
python -m examples.cookbook.run --recipe 04 --output runs/cookbook-personas
```

```bash
python -m orgabm assign-personas --job examples/cookbook/plans/04/stream/job.json --preview
```

## Sources and records

- [pool](../../examples/cookbook/plans/04/pool/job.json)
- [stream](../../examples/cookbook/plans/04/stream/job.json)
- [unfilled](../../examples/cookbook/plans/04/unfilled/job.json)
- [Position-conditioned Persona assignment API](../public_api.md#position-conditioned-persona-assignment)
- [Organizational experiment cookbook](README.md)
