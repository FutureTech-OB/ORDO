# Scale, runtime, cost and reuse evidence

Measurements refer to specific workloads and services. The Harness–Jev–Mesa trial runs six worlds with 1,000 members, four departments and six rounds each: 36,000 new judgments in 576 native batches. Harness wall time is 307.22 seconds; summed simulation execution is 214.48 seconds, with individual worlds taking 33.40–37.36 seconds. Metered Jev cost is $0.79644831, calculated using returned input tokens at the configured $0.042 per million. Research-assistant gateway charges were not priced.

The organizational convention extension runs 12 Jev worlds of 1,000 members, 50 departments and 32 periods, plus 36 rule controls. Its 92,058 judgments have $0.73701138 in successful-response usage.cost. The execution includes pauses and recovery. Sixteen failed transports have no confirmed additional billing amount.

A separate rules-only task workflow runs 10,000 members, 1,000 departments, 9,000 tasks and six rounds in each of two authority configurations. Independent-process runtimes are 6.78 and 4.88 seconds, including initialization and evidence export. It uses short synthetic Personas, sparse reporting and simple task dependencies. Completing the horizon and completing every task are measured separately.

The SDK separates observations, allowed actions and state transitions from judgment. Published LLM cases and 33 conventional-ABM worlds reuse execution, logging and replay facilities. New environments supply an adapter preserving their own causal sequence. This is the demonstrated infrastructure capability; adoption time by unfamiliar researchers remains to be measured.

## Configuration and execution

| Workload | Scale and choices | Time | Decision-engine cost |
| --- | --- | --- | --- |
| Harness–Jev–Mesa organizational learning | 6 worlds of 1,000 members, four departments and six rounds; 36,000 fresh choices in 576 native batches | Harness wall time 307.22 s; summed simulation time 214.48 s; individual worlds 33.40–37.36 s | Metered Jev cost $0.79644831, excluding Harness charges |
| Organizational convention extension | 12 Jev worlds of 1,000 members, 50 departments and 32 periods; 92,058 new judgments, plus 36 rule controls | Run includes pauses and recovery | Successful usage.cost: $0.73701138; 16 unsuccessful transports may incur additional billing |
| Rules-only task workflow | 10,000 members, 1,000 departments, 9,000 tasks and six rounds per world; delegation and manager-review configurations | Independent-process runtimes: 6.78 / 4.88 seconds including initialization and export | Zero model API requests |

## Sources and records

- [Harness–Jev–Mesa organizational trial](harness_jev_trial.md)
- [Harness–Jev execution audit (JSON)](../examples/harness_jev_audit.json)
- [Organizational conventions: recorded results](organizational_conventions/results/README.md)
- [Workflow scale benchmark results (JSON)](../examples/workflow_scale_benchmark.json)
- [Published LLM social simulations through ORDO](llm_abm_cookbook/README.md)
- [Conventional ABM portability cookbook](abm_cookbook/README.md)
- [Public experimental API (v0.6.0)](public_api.md)
