# ORDO

**Organizational Decision Modeling** is an experimental foundation for large-scale organizational agent-based simulation. Organizational structure defines both the institution being studied and the observations, interactions, and decision dependencies used during execution.

ORDO builds on Mesa and connects Personas, positions, departments, reporting relationships, information permissions, tasks, and environmental feedback. Replaceable decision engines supply local choices; the environment executes organizational consequences. A research-agent interface supports configuration, preview, execution, and inspection.

## Start here

- [API and research-agent integration](docs/public_api.md)
- [Organizational convention experiment](docs/organizational_conventions/README.md) · [results](docs/organizational_conventions/results/README.md)
- [Figures and captions](docs/figures/README.md)

## Install

Use Python 3.12 or newer from a source checkout:

```bash
git clone https://github.com/FutureTech-OB/ORDO.git
cd ORDO
python -m venv .venv
# Activate .venv using your operating system's standard command.
python -m pip install -e ".[mesa,harness,cookbooks]"
```

## Published LLM social simulation cookbooks

| Experiment | Run scale | Entry point |
| --- | --- | --- |
| Conventions and committed minorities, *Science Advances* | 24 members; 20 worlds; 28,177 model decisions | [Cookbook](docs/llm_abm_cookbook/behavior_results/README.md) |
| Majority coordination, *Science Advances* | 50 members; 20 worlds; 6,279 model decisions | [Cookbook](docs/llm_scope_review/demarzo_results.md) |
| Repeated games, *Nature Human Behaviour* | 64 two-player matches; 320 model decisions | [Cookbook](docs/llm_scope_review/nhb_sampled_results.md) |
| Network polarization, *Nature Communications* | 1,000 members; 68,161 model decisions | [Cookbook](docs/nc_polarization_live/README.md) |

The organizational extension adds positions, reporting relationships, departmental information permissions, and guidance to the convention-formation experiment. It examines six organizational conditions in a 1,000-member organization and extends the manager-placement condition with formal guidance to 10,000 members across 500 departments. See the [experimental design and results](docs/organizational_conventions/README.md).

Each cookbook specifies observations, memory, actions, timing, feedback, model substitution, and recorded outcomes. Additional rule-based ABM examples provide engineering references and portability demonstrations.

## Verify saved executions

Fetch three pinned public author files for the repeated-games source check, then replay the recorded experiments:

```bash
python -m examples.llm_nhb_original.sources --download
python tools/replay_ordo_v2_review.py
python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/results
python tools/replay_organizational_conventions.py --evidence docs/organizational_conventions/scale_10000/evidence
```

Replay reconstructs original-event inputs, sampled actions, and recorded outcomes from saved judgments. The organizational check also compares complete final individual states. [Evidence manifest](docs/appendix_ordo_v2_evidence/manifest.json).

## Run and customize

```bash
python -m orgabm demo --port 8765
python -m orgabm experiment --plan examples/workflow_plan.json --preview
python -m examples.organizational_conventions.reliable_run --preview
python -m examples.organizational_conventions.reliable_run --output runs/org-rules
```

The browser opens at `http://127.0.0.1:8765/`; the task-workflow view is `/workflow`. Templates and Persona imports are documented in the public API. The SDK accepts existing Mesa models through preparation and commit callbacks, as well as other Python environments through `describe`, `prepare`, and `advance`.

Jev is the first integrated specialized decision engine. Fresh paid inference uses a researcher-supplied environment credential and explicit request/cost allowances. DeepSeek Harness connects through the MCP tools with its own compatible assistant configuration. See [API instructions](docs/public_api.md) and [protocol records](docs/implementation_notes_20261030.md).

## Code layout

| Path | Purpose |
| --- | --- |
| `orgabm/` | SDK, Mesa bridge, organizational components, engines, journals, and research-agent tools |
| `examples/` | Environments, templates, plans, and cookbook entry points |
| `web/` | Browser interface |
| `tests/` | Protocol, component, and runtime checks |
| `tools/` | Replay, analysis, and verification utilities |
| `docs/` | Methods, results, and portable evidence |

## Checks

```bash
python -m unittest discover -s tests -v
python tools/check_mcp.py
```

Reference checks for optional upstream scenarios run when their pinned source caches and optional dependencies are present; the test report lists those skipped in a fresh checkout. The saved-execution replay commands above cover the featured LLM cases and organizational extension.

## Source attribution

ORDO's original code and documentation are released under the [MIT License](LICENSE). Third-party code, datasets, and other incorporated materials remain subject to their respective licenses and terms.

[Third-party notices](THIRD_PARTY_NOTICES.md) and the cookbook source manifests identify incorporated research and code. Upstream license and attribution files are retained alongside redistributed third-party code. Commit authorship for this research artifact is recorded as Anonymous Authors.
