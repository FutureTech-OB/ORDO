# Executed PedNav component check — 2026-10-30

Canonical evidence: `runs/ncs-additional-20261030/release/verification.json`.

The 12 configurations completed: vector/shortest mechanisms × sigma 0/0.7 × seeds 7/11/17, each on all 100 publicly released Boston OD pairs. ORDO generated **1,200 fresh route samples** and recorded **1,200 SDK controller actions**. Independently invoking the original methods generated another 1,200 reference samples; every path matched node for node. Reference samples are verification overhead, not additional population members. Twelve configurations are not twelve interacting populations. Each record is a complete trip, not a behavioral decision at each street intersection.

| Mechanism | Sigma | Mean route/shortest-distance ratio, across the 100 OD pairs (three seeds) |
|---|---:|---|
| Vector | 0 | 1.005287 / 1.005287 / 1.005287 |
| Vector | 0.7 | 1.046798 / 1.076906 / 1.048048 |
| Shortest | 0 | 1.000000 / 1.000000 / 1.000000 |
| Shortest | 0.7 | 1.179030 / 1.177395 / 1.112721 |

These are descriptive checks of the configured mechanism on this released sample. They do not establish that vector navigation fits human decisions better: no human-model fit test or parameter calibration was performed. The original Boston graph contains 78,402 nodes and 112,527 edges. No San Francisco graph, private GPS data, new organizational interaction, Jev or LLM call was used.

Observed local time: 63.676 s for the sweep and its reference checks after graph loading; 34.436 s summed ORDO execution/export and 29.081 s summed direct native reference calls. Interpreter/dependencies: Python 3.12.14, NumPy 2.3.5, igraph 0.11.9. Download, dependency installation, graph initialization and tests are excluded. This is not a general speed or cloud-cost benchmark. Recorded model API calls and API cost were both zero.

Four tests passed: direct author calls vs SDK, restoration of NumPy random state, invalid commit preserving state, rejection of an unapproved pickle constructor. The read-only verifier confirmed all five frozen adapter source hashes and 63 output hashes. The author code/data and license hashes are recorded separately in `source_manifest.json`.

Re-run from the repository root after installing `igraph==0.11.9`:

```powershell
python -m examples.ncs_additional_mobility.run --download --trip-limit 100 --output runs/pednav-repeat
python -m examples.ncs_additional_mobility.verify runs/pednav-repeat
```

The source release is GPL-3.0 and is fetched into an ignored cache rather than vendored. See the cookbook README for exact version, data attribution and redistribution boundaries.
