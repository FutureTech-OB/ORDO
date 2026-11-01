# Local verification — updated 2026-10-17

- Initial v0.2.1 check: 19 unit/integration tests passed, including Mesa/reference trajectory equivalence, information boundaries, synchronous updates, permissions, accounting, experiment grids, gateway configuration and a custom environment unrelated to the organization kernel. Current v0.2.2 has 21 passing tests (see below).
- Official MCP Python client completed discovery of five tools, experiment preview, background execution, result retrieval and inspection of decision `t2_a0` through the actual stdio transport.
- DeepSeek HTTP payload, JSON action parsing and request cap were verified with mocked responses, followed by a live test through the user-selected gateway: one probe and 48 agent decisions. A separate model-driven MCP planning test used three calls including one rejected plan-schema attempt.
- Browser: archived Jev results displayed; two 2,400-decision free runs compared; configuration and result downloads parsed; employee and round inspection worked. The foundation interface page was rendered and inspected.
- Original policy ABM source remained unchanged (SHA-256 recorded in provenance).
- The original local CLI completed 2,400 free decisions with saved results.

Verification runtime: Python 3.12.9, Mesa 3.5.1, MCP SDK 1.30.0. Optional packages were installed inside the project's ignored `.deps` directory for these checks; the base Python environment was not upgraded. Standard installation instructions use an isolated virtual environment.

Update v0.2.2: 21 tests and the MCP protocol check pass, including native Jev batch counts, process cost guard, provider restrictions, metadata and bounded status waiting. An actual official DeepSeek Harness headless conversation completed 2 rule worlds and 48 decisions. The exact plan, reported key numbers and all six round metrics were audited; see harness_trial.md. No additional chat-model agent decisions were requested.

2026-10-16: the official Harness host completed a live Jev/Mesa experiment with 1,000 agents × 6 rounds × 2 contact conditions × 3 paired seeds. All 576 native batches and 36,000 probabilities were reconciled; all 36 round metrics replayed exactly. The six reported rows and aggregate requests/cost matched artifacts. See harness_jev_trial.md and examples/harness_jev_audit.json.

Not tested: other organization extensions with live Jev; arbitrary ABMs through Harness; production-scale Harness reliability; hosted deployment; GitHub CI. A CI workflow is supplied, and the repository remains local by the owner's choice. These integration trials do not establish human-behavior validity or comparative performance against ordinary LLM agents.

2026-10-16 reusable templates: all five starter plans passed `expand_plan` validation at their saved default sizes. Small smoke variants (16 agents, three rounds, seed 7) completed through the existing Mesa experiment service: nine worlds and 432 decisions, no model API requests. Every declared metric exists in output; all recorded questions expose three coworkers, with siloed/bridge department composition checked. This verifies executable configurations and contact mechanisms, not the full default workloads or behavioral validity. Local audit: `runs/template-smoke-c9319a341a094222bb4b22aa34a238ad/audit.json`. No application runtime code changed.

2026-10-16 v0.3.0 Persona integration:

- All 33 unit/integration tests passed with Mesa 3.5.1 and MCP available (none skipped). Added checks for dataset schema fixtures, CSV/custom maps, JSONL, rejection of invalid records/sampling, paired populations, role permissions, custom department contacts, reporting-cycle rejection, private information boundaries and roster provenance.
- The real `JevEngine` batching/HTTP serialization path was exercised with mocked provider responses: eight agents × two rounds, six batches of at most three questions, 16 distinct question IDs with the correct private Persona and current role. No live provider calls were made.
- The actual MCP stdio client previewed and ran a Persona plan and inspected `t2_a0`, confirming Persona and organization in its question. This is a protocol integration check, not a new model-driven Harness host trial.
- Browser checks on the v0.3.0 preview at port 8766: loaded the fictional 16-person example, previewed four departments and manager/member assignments, completed three rounds / 48 free rule decisions, inspected Persona and reporting cues in the local observation, and imported a two-row fictional CSV through custom column mapping.
- `node --check web/app.js` passed. Python/CLI and browser share the same input validation/importers. Source dataset rows are not bundled; built-in adapters were tested on fictional schema fixtures. Persona-dependent behavior with live Jev and human validity remain unmeasured.

2026-10-16 v0.4.0 position-conditioned population construction:

- All 42 unit/integration tests passed with Mesa 3.5.1 and MCP available (none skipped). Checks cover the inclusive 0.5 threshold, weighted full-pool allocation, fixed quotas, unique assignments, evaluation limits, incomplete outputs, frozen role layouts across world seeds and private provenance.
- The actual JevEngine serialization/batching path was tested with mocked HTTP responses. No live provider requests were made for position probabilities.
- The actual MCP stdio client discovered seven tools, previewed the 24-candidate/eight-slot assignment, confirmed paid starts are disabled by default, and completed the existing free Mesa/Persona run and decision inspection. This is a protocol check, not a new Harness model trial.
- Browser preview/export showed 24 candidates, eight slots (two managers and six engineers), at most 48 candidate/role judgments and two native requests. Pool mode disables the threshold control. Browser previews are free; CLI or explicitly enabled MCP runs execute Jev assignments.
- Model scores remain uncalibrated. These checks establish implementation behavior, not representative sampling of actual job populations.

2026-10-16 v0.5.0 executable organization design:

- All 54 unit/integration tests passed with actual Mesa 3.5.1 and MCP dependencies. New checks cover authority and approval timing, finite review/worker capacity, dependency blocking, revisions and renewed approval, budget contention, reward conservation, private observations, stage failures, saved-probability replay, workflow Persona assignment and service validation.
- The real JevEngine HTTP/batch path was exercised with mocked responses. Questions have fresh IDs, and no batch crosses a dependent stage boundary. No live Jev or Harness-assistant API calls were made for this new scene.
- The actual MCP stdio client discovered seven tools, completed the existing NK check plus two free workflow worlds, and inspected manager decision `t1_review_0_a0`.
- The browser workbench at `/workflow` loaded the editable templates, previewed the roster/tasks, completed six paired free worlds, displayed the results and inspected a manager's submitted dossier. Browser console errors: zero. Screenshot: `docs/workflow-preview.png`.
- The public `python -m orgabm experiment` CLI independently completed the same six-world plan: 234 actual decisions and zero provider requests. Centralized approval accumulated 9, 9 and 11 task-wait ticks for seeds 7, 8 and 9; delegation accumulated zero. Both conditions completed 12 tasks, with net outcomes 72, 72 and 64. This is a mechanical baseline check, not evidence that delegation improves human organizations. Audit: `runs/workflow-cli-27b7a25492b34e618f658178a969dbb7/audit.json`.
- Stage commits and evidence are retained if a later stage fails; a partial round is not reported as complete. Replay reproduces completed-round metrics from saved probabilities. Automatic rollback, retry/resume, live-model behavioral validity, committee/matrix mechanisms and dynamic restructuring are not implemented by this increment.

## v0.5.1 scale benchmark

2026-10-16: all 56 tests passed. New regression coverage compares each reward transaction and subsequent local balance observation with explicit per-member accounting, across individual/common reward weights. The large-plan fixture validates multi-level reporting, departments, tasks and Persona assignment. Shared rewards now use a single per-member offset plus individual balances, removing the population-wide loop from each transaction. Complete balance export is still linear in population. Floating-point accumulation order may differ at low precision.

Each workload below ran once in a fresh process on the same local Windows 11 machine, Python 3.12.14 and Mesa 3.5.1. Times include plan expansion, initialization, simulation and full trace/result/snapshot writes; they exclude Python startup and library imports. Peak working-set memory includes imported libraries. These are single observations, not latency distributions or cross-machine performance guarantees.

| Members | Departments / tasks | Mode | Rounds | Fresh rule decisions | Total seconds | Peak memory MiB | Saved evidence MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1,000 | 100 / 900 | Delegated | 6 | 5,400 | 0.621 | 133.8 | 11.56 |
| 1,000 | 100 / 900 | Reviewed | 6 | 3,000 | 0.465 | 127.7 | 7.27 |
| 10,000 | 1,000 / 9,000 | Delegated | 6 | 54,000 | 6.781 | 375.9 | 116.59 |
| 10,000 | 1,000 / 9,000 | Reviewed | 6 | 30,000 | 4.883 | 317.2 | 73.21 |

Each department has nine workers and a manager; department heads form a sparse reporting tree. Personas are short synthetic records. Every worker has one independent task requiring six work ticks. Delegated workers start at tick one, whereas manager-approved work starts the next tick. Therefore no reviewed task finishes within this six-tick stress window; this is intentional workload construction, not evidence about comparative organizational performance. Tasks have deterministic success here, with no cross-task dependency edges. Deep hierarchies, long Persona descriptions, dense task dependencies, longer horizons and repeated worlds require separate benchmarks.

There were **zero provider requests**. These numbers do not measure Jev latency/cost/rate limits, MCP/browser throughput, paid inference, sustained job recovery, multi-organization competition or external markets. Current service limits still apply: 10,000 members and 10,000 tasks per workflow world, 200 worlds and two million decision opportunities per plan; the browser uses smaller preview/demo limits. No 100,000-member run was attempted.

Reproduce from the repository root, with the Mesa extra installed:

```bash
python -m tools.benchmark_workflow_scale --sizes 1000 10000 --rounds 6 --modes delegated reviewed --output runs/new-scale-run
python -m examples.large_organization --agents 1000 --output runs/large-plan.json
python -m orgabm experiment --plan runs/large-plan.json --preview
```

Use a new output directory/file. The benchmark writes one world and summary per case plus `benchmark.json`. This run's full local evidence is in `runs/workflow-scale-f60162bfa71241edbece3f7ca9abcb10/`; its small portable summary is [`examples/workflow_scale_benchmark.json`](../examples/workflow_scale_benchmark.json). The next scale priorities are evidence partitioning/indexing, bounded question/batch buffers, explicit checkpoint/recovery semantics and controlled world-level parallelism. Runtime success at 10,000 agents does not remove these limits.

## v0.6.0 organizational memory permissions

2026-10-16: all 67 tests passed. Eleven new cases cover organization/department/personal isolation, role/department selector conjunction and selector-list alternatives, explicit cross-department exceptions, default-denied roots, inherited and capped child grants, summary/full-content separation, inclusive release windows, expiry, malformed/cyclic policies, context budgets, trusted roster identity and input-copy isolation.

The real Jev adapter serialized member-specific memory views through mocked HTTP responses; no live provider call was made. Stage logs were checked against exact input views and visibility hashes. Repeated free runs reproduced metrics. The actual MCP stdio client ran the memory template and confirmed the first-round employee lacks the demand report while the manager receives its full text, with visibility evidence recorded in stage effects.

The browser selected the new template and verified member 1 at rounds 1, 3 and 5: the demand record was absent, then summary-only, then full text. Member 4 (another department's manager) could access the organization report but not department 0 or member 1 records. A free six-round world completed 51 decisions, 11 completed/successful tasks, 4 blocked tasks and net value 64; these are baseline mechanics, not an effect of memory because the rule ignores its text. The decision inspector showed manager input and its six-node audit. Browser console errors/warnings: zero. Screenshot: `docs/memory-permissions-preview.png`.

This increment validates read permissions and actual context construction. It does not validate a model's understanding/beliefs, live Jev responses to information asymmetry, active information-seeking, dynamic memory writing, automated redaction, or memory-enabled ten-thousand-member throughput. Researcher configuration and audit files retain the full store; simulated actors receive filtered views only.

## Readiness recheck 2026-10-17

- Python 3.12.14 with existing project-local Mesa 3.5.1 / MCP 1.30.0 dependencies: all 67 tests passed in 3.155 seconds, with no skips. This includes local HTTP endpoint checks and mocked provider serialization, not live inference.
- `tools/check_mcp.py` passed over actual stdio transport: seven tools; one Persona/NK world; two workflow worlds; one memory world; Persona inclusion and member/manager memory visibility checked through decision inspection.
- The initial bare-runtime test attempt could not load optional Mesa dependencies and encountered sandbox loopback/temp-directory restrictions. The successful run loaded `.deps`, placed test temporary files in `.buildtmp/readiness-tests`, and used approved local process/loopback access. The MCP recheck also required the existing PyWin32 subdirectories on the process search path. No dependency or application code was changed. This is not a clean-install verification.
- Reviewed the saved 36,000-decision / 576-batch Harness–Jev audit and 1,000/10,000-member rule benchmark summaries. Those are earlier measurements, not new provider or scale runs. No new Harness model conversation, browser visual inspection or live provider request was performed.
- Runtime scope remains two single-organization scenes; composite organizations, market feedback and automatic recovery remain pending.
