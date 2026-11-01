# Conventions, positions, and publishing permissions in a large organization

How does the placement of the same committed minority, combined with publishing rights, change convention diffusion? This example extends the naming game with positions, reporting contacts, and departmental memory permissions. Its independent experimental worlds use the same organizational specification.

## Organization and treatments

The factorial experiment uses 1,000 members in 50 departments of 20; the manager-placement condition with formal guidance is also evaluated at 10,000 members in 500 departments. In the factorial experiment, one executive also heads HQ; the other 49 managers report to the executive. Employees report to their department head. A shared neutral synthetic Persona separates personal description from position; custom populations can be imported through the population interface.

Twenty committed members always choose M, one in each of 20 non-HQ departments. The other 980 choose Q or M; the larger population retains the same 2% committed share, with 200 committed managers and 9,800 ordinary members. Employee and manager placement use the same selected departments and, within each seed, the same contact schedules. Publishing authorization is assigned separately from position.

Placement crosses no guidance, peer guidance, and formal guidance. Peer and formal messages recommend M with identical content, departmental readers, and exposure. Formal messages require a validated publishing grant. Members choose voluntarily; payoffs depend on their paired actions. MemoryForest.observe filters records by department and release time. Notices are persistent, researcher-configured records.

## Interaction and measurement

Each period schedules 125 disjoint pairs in the 1,000-member organization and 1,250 in the 10,000-member organization, prioritizing reporting contacts while retaining departmental and cross-department encounters. Fallback channels are recorded. Rotating initiators and contact randomness are independent of actions, aligning contacts across the six treatments within each seed.

Choices are collected before simultaneous settlement: matching choices earn +100 each and mismatches -50 each. Members retain their last five interactions. Thirty-two periods produce 4,000 pairings per factorial world and 40,000 in the larger organization, averaging eight participations per person. This period schedule extends the source's pairwise asynchronous process.

Measures include ordinary members' latest M choices, diffusion inside and outside seeded departments, departmental differences, coordination, payoffs, contacts, notice exposure, and coverage. Q and M have symmetric payoffs.

## Conditions and results

Six conditions with two seeds yield 12 Jev worlds and 36 rule-control worlds. Uniform choice measures chance behavior; history follows recent opponent majorities; notice follows formal guidance when visible and otherwise uses history. The completed Jev arm contains 92,058 fresh judgments. Under formal guidance, ordinary-member M shares are 6.3% for employee placement and 22.8% for manager placement; the latter reaches 57.1% in seeded departments and 1.0% elsewhere, compared with 59.89% and 1.28% in the 10,000-member run, where overall adoption is 24.01%. Placement varies contacts and role context together.

## Execution and recovery

The reliable runner previews the plan and defaults to free rules. Paid Jev execution requires OPENROUTER_API_KEY and explicit allowances. Retryable transport failures and 408/429/500/502/503/504 receive at most three exponential-backoff retries with jitter and Retry-After handling. A 402 is retried only when explicitly identified as an in-flight budget condition with Retry-After. Authentication, credit, certificate, parameter, and invalid-result errors terminate execution. Attempts share the original request and cost limits.

Recovery rebuilds completed periods and matches saved original-event inputs before recovering judgments. Missing events receive new calls; mismatched inputs stop recovery. The runner reads the original limits. Earlier run/resume implementations remain available for recorded-source checks. This scenario runs through the Python SDK.

## Research context

The extension builds on Ashery et al. and relates to prior work on memory, networks, scale, and minority placement. Its organizational design combines roles, reporting contacts, departmental information boundaries, and publishing grants. Multi-organization interaction and environment-dependent performance learning are future extensions.

## Configuration and execution

| Factor | Condition | Definition |
| --- | --- | --- |
| Position | employee / manager | Committed members occupy employee or manager positions, changing contacts and role context. |
| Guidance | none | Interaction and personal history only. |
| Guidance | peer | Peer guidance visible within the department. |
| Guidance | official | Formal guidance with matched content and readers; publishing rights are validated. |

```bash
python -m examples.organizational_conventions.reliable_run --preview
python -m examples.organizational_conventions.reliable_run --output runs/org-conventions-rules
# Configure your own OPENROUTER_API_KEY in the process environment:
python -m examples.organizational_conventions.reliable_run --engine jev --allow-paid --max-retries 3 --timeout 90 --concurrency 2 --max-cost-usd 3 --max-requests 6000 --output runs/org-conventions-live
python tools/analyze_organizational_conventions.py --run runs/org-conventions-live
```

```bash
python -m examples.organizational_conventions.resume_reliable --allow-paid --run runs/org-conventions-live
```

## Sources and records

- [Execution entry point](../../examples/organizational_conventions/reliable_run.py)
- [Organizational conventions: recorded results](results/README.md)
- [Organizational convention model](../../examples/organizational_conventions/model.py)
- [Population and position assignment module](../../orgabm/workforce.py)
- [Organizational memory and information permissions](../../orgabm/memory.py)
- [Model request and retry handling](../../orgabm/openrouter_reliable.py)
- [Decision logging module](../../orgabm/decision_journal.py)
- Experiment configurations: [1,000 members](../../examples/organizational_conventions/large_plan.json); [10,000 members](scale_10000/plan.json)
- [Source paper](https://doi.org/10.1126/sciadv.adu9368)
- [Exploring the Topology and Memory of Consensus: How LLM Agents Agree, Fragment, or Settle When Forming Conventions](https://arxiv.org/abs/2606.04197)
- [Network topology shapes consensus and vulnerability in LLM populations](https://arxiv.org/abs/2610.31165)
