# Information permissions and release timing

Compare manager-only information with shared disclosure at rounds 1 and 3. Cross these conditions with an information-responsive rule and a memory-blind control, over three seeds: 18 worlds. Permission filtering occurs before information enters a member's observation.

Under the responsive rule, early sharing increases mean completed tasks from 14.667 to 18 and net returns from 73.333 to 99.333. Sharing at round 3 produces intermediate outcomes. The memory-blind control has identical outcomes across disclosure conditions: 21 completed tasks and net return 44.667. The contrast checks that effects operate through the intended information-consuming policy.

## Configuration and execution

| Policy | manager | Department employees |
| --- | --- | --- |
| `manager_only` | Full report readable from round 1 | No access |
| `shared_now` | Full report readable from round 1 | Full report readable from round 1 |
| `shared_round_3` | Full report readable from round 1 | Full report readable from round 3 |

| Disclosure under information-responsive rules | Cumulative requests | Total waiting | Completed tasks | Net value |
| --- | --- | --- | --- | --- |
| only manager | 27.00 | 76.33 | 14.67 | 73.33 |
| Employees can read immediately | 18.00 | 22.33 | 18.00 | 99.33 |
| Employee access from round 3 | 23.33 | 57.00 | 15.67 | 79.33 |

```bash
python -m examples.cookbook.run --recipe 03 --output runs/cookbook-disclosure
```

## Sources and records

- [information_rule](../../examples/cookbook/recipes.py)
- [Organizational experiment cookbook](README.md)
