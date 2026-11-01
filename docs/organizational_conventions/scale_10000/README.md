# Organizational convention formation at 10,000 members

This run extends the [organizational convention experiment](../README.md) to 10,000 members in 500 departments. It uses the manager-placement condition with formal guidance, 200 committed managers, and 32 periods. The experiment contains 40,000 pairings and 74,693 model decisions.

Ordinary members' final adoption of the new convention is 24.01% overall, 59.89% in departments containing committed managers, and 1.28% elsewhere. These rates exclude committed members. The Jev simulation stage took 358.14 seconds.

## Records

- [Plan](plan.json): population, organization, treatment, and seed.
- [Results](summary.csv) and [detailed summary](summary.json).
- [Trajectories](trajectory.csv): period-level outcomes.
- [Performance](performance.json), [measurement provenance](measurement_provenance.json), and [execution environment](environment.json).
- [Replay evidence](evidence/replay_manifest.json) and [verification record](replay_verification.json).

The records retain the main Jev run and accompanying rule-based runs. Local machine paths in the summary and measurement provenance have been replaced with `<run_directory>`; numerical results and replay evidence are unchanged.

## Verify

From the repository root:

```bash
python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/scale_10000/evidence
```

Verification reconstructs inputs, period metrics, and final individual states using saved decisions. It does not make new model calls.
