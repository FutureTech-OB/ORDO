# Population scale and interchangeable engines

The local baseline compares approval and delegation at populations 100 and 1,000. It records action questions, delivered tasks, returns, runtime and exported bytes. All four worlds use rules, with no model API calls. A separate large-organization benchmark extends the same workflow to 10,000 members.

At 1,000 members, approval produces 4,500 questions and delegation 2,700; both complete 900 tasks with net return 5,400. Recorded local runtimes are 0.526 and 0.381 seconds. Saved plans can switch decision engines while preserving the organization and environment; model-service latency and charges must then be measured for that run.

## Configuration and execution

| Population | Institution | Actual choices | Final completed tasks | Tasks past deadline | Local runtime |
| --- | --- | --- | --- | --- | --- |
| 100 | Approval | 450 | 90 | 40 | 0.063 seconds |
| 100 | Delegation | 270 | 90 | 0 | 0.048 seconds |
| 1,000 | Approval | 4,500 | 900 | 400 | 0.526 seconds |
| 1,000 | Delegation | 2,700 | 900 | 0 | 0.381 seconds |

```bash
python -m examples.cookbook.run --recipe 05 --output runs/cookbook-scale
```

```bash
python -m examples.cookbook.run --recipe 05 --scale-agents 10000 --export-only --output runs/cookbook-scale-10000-inputs
```

```bash
python -m orgabm experiment --plan examples/cookbook/plans/02/delegation_x_capacity/jev-plan.json --preview
```

```bash
python -m orgabm experiment --plan examples/cookbook/plans/02/delegation_x_capacity/jev-plan.json --max-requests 360 --max-cost-usd 0.10 --output runs/cookbook-approval-jev
```

## Sources and records

- [Organizational experiment cookbook](README.md)
