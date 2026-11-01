# Network-polarization source records

The adapter reconstructs author-recorded network and opinion states for three topics and 41 snapshots each. It covers 123 snapshots, 491,474 contact rows and 120,000 state assignments, with no model API calls. This archive check establishes data loading and state-transition compatibility.

The fresh 1,000-member Jev and DeepSeek simulation is documented in nc_polarization_live. Its newly generated choices and messages are independent of this source-record replay.

## Configuration and execution

| Topic | Figure conditions matched by public snapshots | Neutral share: initial → final | Mean absolute opinion: initial → final |
| --- | --- | ---: | ---: |
| Partisan alignment | Correction / self-regulation (Figure 2d) | 40.2% → 32.8% | 0.824 → 1.292 |
| Gun control | Baseline (Figure 1) | 39.6% → 0.4% | 0.803 → 1.582 |
| Abortion ban | Correction / self-regulation (Figure 2d) | 39.7% → 11.3% | 0.843 → 1.732 |

```bash
python -m examples.nc_polarization.run --download --output runs/nc-polarization-local
python -m unittest discover -s tests -p test_nc_polarization.py -v
```

```bash
python -m examples.nc_polarization.replay --evidence docs/nc_polarization/results
```

## Sources and records

- [Network polarization with Jev and conditional DeepSeek content](../nc_polarization_live/README.md)
- [Emergence of polarization in networks of large language model agents](https://doi.org/10.1038/s41467-026-78228-y)
- [Source repository](https://github.com/tsinghua-fib-lab/LLM_for_Polarization)
- [Verification report (JSON)](results/verification.json)
- [Simulation trajectories (CSV)](results/trajectories.csv)
- [Archived polarization trajectories (figure)](results/polarization_archive.png)
- [Network-polarization source model adapter](../../examples/nc_polarization/model.py)
