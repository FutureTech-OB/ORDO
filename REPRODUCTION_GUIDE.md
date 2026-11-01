# ORDO reproduction guide

This file is the entry point for the experiments and materials described in Technical Appendix A2, A3, and A5. All links below are relative to the repository root and remain usable in a downloaded checkout.

## A2 experiment and file index

The labels in the last column of the appendix table correspond to the following files and directories.

| Experiment | Methods, results, and protocol notes | Exported records |
| --- | --- | --- |
| Conventions and collective bias | [Methods and results](docs/llm_abm_cookbook/behavior_results/README.md) | [Exported records](docs/appendix_ordo_v2_evidence/naming/) |
| Majority coordination | [Results](docs/llm_scope_review/demarzo_results.md); [protocol audit](docs/llm_scope_review/sa_original.md) | [Exported records](docs/appendix_ordo_v2_evidence/majority/) |
| Repeated games | [Sampled-arm results](docs/llm_scope_review/nhb_sampled_results.md); [source audit](docs/llm_scope_review/nhb_original.md) | [Exported records](docs/appendix_ordo_v2_evidence/games/) |
| Network polarization | [Adapter and differences / protocol notes](docs/nc_polarization_live/README.md) | [Execution record](docs/appendix_ordo_v2_evidence/polarization-partial/verification.json) |

The [evidence manifest](docs/appendix_ordo_v2_evidence/manifest.json) identifies the saved files. The [verification report](docs/appendix_ordo_v2_evidence/replay_verification.json) records the source-experiment replay checks.

## A3 organizational experiment

| Material | Relative entry point |
| --- | --- |
| Organizational experiment cookbook and design | [docs/organizational_conventions/README.md](docs/organizational_conventions/README.md) |
| 1,000-member experiment records | [docs/organizational_conventions/results/README.md](docs/organizational_conventions/results/README.md) |
| 10,000-member experiment records | [docs/organizational_conventions/scale_10000/README.md](docs/organizational_conventions/scale_10000/README.md) |
| 10,000-member verification record | [docs/organizational_conventions/scale_10000/replay_verification.json](docs/organizational_conventions/scale_10000/replay_verification.json) |

The experiment directories provide plans, results, trajectories, performance records, and saved decisions used for replay. Follow each entry point for the corresponding files and run configuration.

## A5 installation and replay

Use Python 3.12 or newer. Run the following from the root of a source checkout:

```bash
python -m venv .venv
# Activate .venv using the command for your operating system.
python -m pip install -e ".[mesa,harness,cookbooks]"
```

Fetch the pinned public author files needed by the repeated-games source check, then verify the recorded experiments:

```bash
python -m examples.llm_nhb_original.sources --download
python tools/replay_ordo_v2_review.py
python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/results
python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/scale_10000/evidence
```

These commands reconstruct recorded executions from saved decisions. Fresh model runs are described in the individual cookbooks and require the appropriate model credentials and request/cost allowances.

## Interfaces and further use

- [Public API and research-agent integration](docs/public_api.md)
- [Figures and captions](docs/figures/README.md)
- [Project overview and browser interface](README.md)

For fresh organizational runs and previews, see the organizational experiment cookbook above. Use the documented configuration and a new output directory for each run.
