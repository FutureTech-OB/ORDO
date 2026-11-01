# Original NCS configuration tracking

Original source configurations are recorded before running mobility, colocation and dynamic-network cases. Population, horizon, update timing, source dependencies and expected workload are kept separately from reduced pilots. The tables below preserve the recorded preparation and run states. Native reference execution and fresh Jev choice transfer are distinguished in their respective manifests.

## Configuration and execution

| Task | Source configuration or public entry point | Conditions retained | Known requirements |
| --- | --- | --- | --- |
| Urban mobility, NCS 2021 | Source main: 30,000 members, 300×300 grid, five repetitions, 20,001 periods each | Original exploration/return rules, full space and frozen-population timing; 3,000,150,000 individual updates in the code configuration | The paper reports 20,000 periods; code adds a flush period. The displacement menu contains 71,608 entries and 71,538 unique destinations, retained without deduplication. |
| Organizational communication, NCS 2022 | Article: 2,834 members; stage edge counts N(1000,10) and N(500,10). Public capsule has a separate demo schedule. | Original MIT configuration requires private population, candidate-edge and distance data. Public capsule: 52 shared days, 377 remote days, 38 return days and a 415-day colocated counterfactual; 882 daily updates. | Private full-MIT inputs are unavailable. The public demo uses 50+shift and 20+shift with shift=int(N(0,3)), 1,577 candidate historical edges and 436 endpoints. |
| Dynamic networks, NCS 2026 | Extended Data Fig. 2: 10 independent MC runs per point, 10^8 death–birth/network events each | Core–periphery topology, parameters, burn-in, full neighbors, update order and 10 repetitions | Full figure-generation drivers are unavailable. The generic Julia kernel can support explicitly documented reconstruction of structure and scheduling. |

## Sources and records

- [Typesafe Choice API documentation](https://docs.typesafe.ai/primitives/choice)
- [Structure-coefficient theorem for evolutionary games on dynamic networks](https://www.nature.com/articles/s43588-026-01068-9)
