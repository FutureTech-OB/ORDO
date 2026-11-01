# Delegation and managerial capacity

Cross delegation limits 0 and 2 with one or two review slots per manager, using three seeds: 12 worlds. Employees propose tasks, managers process the queue, and the environment executes authorized work and settles payoffs. Pending approvals consume time even when projects and personnel are otherwise identical.

All four baseline conditions average 12 completed tasks and net return 69.333. Without delegation, average approval waiting falls from 9.667 to 3 when review capacity doubles. Delegation eliminates approval requests in this workload. Inspect stage-level records to connect proposed actions, authorization and delivery.

## Configuration and execution

| Factor | Condition 1 | Condition 2 |
| --- | --- | --- |
| `delegation_limit` | 0: tasks require approval | 2: employees directly start tasks costing at most 2 |
| `review_capacity` | One review per manager per round | Two reviews per manager per round |

| Delegation limit | Reviews per period | Total waiting | Completed tasks | Net value |
| --- | --- | --- | --- | --- |
| 0 | 1 | 9.67 | 12 | 69.33 |
| 0 | 2 | 3.00 | 12 | 69.33 |
| 2 | 1 | 0 | 12 | 69.33 |
| 2 | 2 | 0 | 12 | 69.33 |

```bash
python -m examples.cookbook.run --recipe 02 --output runs/cookbook-approval
```

## Sources and records

- [plan.json](../../examples/cookbook/plans/02/delegation_x_capacity/plan.json)
- [Population scale and interchangeable engines](05_scale_and_engines.md)
- [Organizational experiment cookbook](README.md)
