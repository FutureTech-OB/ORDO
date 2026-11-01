# Recorded organizational cookbook results

The local suite completes 50 simulation worlds plus three population-construction jobs. Twelve worlds study knowledge and authority, 12 delegation and review capacity, 18 information permissions, four follow fixed population assignment, and four compare scale and engines. The recorded implementation passed 73 tests at that version.

These free-rule experiments check organizational mechanisms and export reproducible evidence without model-service charges. All condition means, seeds, workloads and exported sizes are retained in the tables below and in verification.json. The current repository's test suite includes subsequent development.

## Configuration and execution

| Contact mode | Adoption threshold | Endpoint outcome | Cumulative net payoff | Cross-department adoptions | Total rejections |
| --- | --- | --- | --- | --- | --- |
| Within department | 0 | 48.158 | 873.347 | 0 | 0 |
| Within department | 10 | 51.489 | 897.331 | 0 | 603.333 |
| Cross-department bridges | 0 | 61.990 | 1079.848 | 185.000 | 0 |
| Cross-department bridges | 10 | 60.124 | 1044.056 | 118.333 | 568.667 |

| Delegation limit | Review capacity | Completed tasks | Net value | Total waiting | Total requests |
| --- | --- | --- | --- | --- | --- |
| 0 | 1 | 12 | 69.333 | 9.667 | 14 |
| 0 | 2 | 12 | 69.333 | 3.000 | 14 |
| 2 | 1 | 12 | 69.333 | 0 | 0 |
| 2 | 2 | 12 | 69.333 | 0 | 0 |

| Rule | Employee report-release time | Completed tasks | Net value | Total waiting | Total requests |
| --- | --- | --- | --- | --- | --- |
| Information-responsive rule | Not provided | 14.667 | 73.333 | 76.333 | 27.000 |
| Information-responsive rule | Round 1 | 18.000 | 99.333 | 22.333 | 18.000 |
| Information-responsive rule | Round 3 | 15.667 | 79.333 | 57.000 | 23.333 |
| Memory-blind control | Not provided | 21.000 | 44.667 | 72.000 | 27.000 |
| Memory-blind control | Round 1 | 21.000 | 44.667 | 72.000 | 27.000 |
| Memory-blind control | Round 3 | 21.000 | 44.667 | 72.000 | 27.000 |

| Case | State | Assigned members | Candidate–position evaluations |
| --- | --- | --- | --- |
| Weighted pool assignment | complete | 12 | 48 |
| Streaming assignment, threshold 0.5 | complete | 12 | 20 |
| Streaming assignment, threshold 0.95 | incomplete | 0 | 48 |

| Population | Institution | Decisions | Completed tasks | Net value | Runtime (s) | Event-log bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 100 | Approval | 450 | 90 | 540 | 0.063 | 752870 |
| 100 | Delegation | 270 | 90 | 540 | 0.048 | 475730 |
| 1000 | Approval | 4500 | 900 | 5400 | 0.526 | 7348250 |
| 1000 | Delegation | 2700 | 900 | 5400 | 0.381 | 4543720 |

```bash
python -m examples.cookbook.run --recipe all --output runs/cookbook-reproduction
python -m unittest discover -s tests -v
```

## Sources and records

- [Verification report (JSON)](verification.json)
- [Organizational experiment cookbook](README.md)
