# Verified conventional-ABM results

All 33 declared worlds complete 645 rounds and 80,511 questions with no model API calls. Wealth, cooperation, segregation and organizational learning match their specified reference checks. The verification artifact records per-world checks and source versions. The tables below preserve the measured configurations and outcomes.

## Configuration and execution

| Model | Condition | Metric | Three-world mean |
| --- | --- | --- | --- |
| wealth | default | gini | 0.6363 |
| schelling | default; parameter=0.3 | same_type_neighbor_share | 0.7300 |
| schelling | default; parameter=0.6 | same_type_neighbor_share | 0.9561 |
| cooperation | Simultaneous; parameter=1.2 | cooperation_share | 0.3241 |
| cooperation | Simultaneous; parameter=1.8 | cooperation_share | 0.0000 |
| cooperation | Random; parameter=1.2 | cooperation_share | 1.0000 |
| cooperation | Random; parameter=1.8 | cooperation_share | 0.0000 |
| cooperation | Sequential; parameter=1.2 | cooperation_share | 0.3333 |
| cooperation | Sequential; parameter=1.8 | cooperation_share | 0.3333 |
| organization | siloed | gross_performance | 48.1576 |
| organization | bridge | gross_performance | 61.9905 |

```bash
python -m examples.abm_cookbook.run --cases examples/abm_cookbook/cases.json --output runs/abm-portability-reproduction
python -m unittest discover -s tests -v
```

## Sources and records

- [verification.json](verification.json)
- [Conventional ABM portability cookbook](README.md)
