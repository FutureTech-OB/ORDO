# Knowledge boundaries and adoption authority

Compare siloed and bridge contacts crossed with adoption thresholds 0 and 10. Three paired seeds produce 12 organizational-learning worlds. This separates access to others' solutions from permission to adopt an improvement. Record performance, cumulative returns, cross-department adoption and rejected proposals.

The free rule baseline shows higher final performance with bridge contacts at both thresholds. Means and all configurations are retained below. These results describe the implemented learning mechanism under its specified decision policy.

## Configuration and execution

| Factor | Condition 1 | Condition 2 |
| --- | --- | --- |
| Contact network `contact` | `siloed`: three department peers | `bridge`: two department peers and one cross-department peer |
| Adoption threshold `approval_gain` | 0: positive improvements may be adopted | 10: copying requires the higher improvement threshold |

```bash
python -m examples.cookbook.run --recipe 01 --output runs/cookbook-knowledge
```

## Sources and records

- [02](02_delegation_and_capacity.md)
- [plan.json](../../examples/cookbook/plans/01/contact_x_permission/plan.json)
- [Knowledge and adoption authority: recorded results](verified_results.md#configuration-and-execution)
- [Organizational experiment cookbook](README.md)
