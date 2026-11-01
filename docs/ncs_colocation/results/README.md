# Checked public-demo results

The completed run covers **12 worlds**, **660 native simulation days**, and **45,918 selected communication edges**, with **zero external decision requests or API calls**. These edge draws are native coupled network transitions, not independent LLM/Jev decisions. Each run includes an ORDO execution, an independent call of the original author `transform` for every phase, and a deterministic SDK reconstruction.

All daily graph nodes and edges, weak-tie counts, component counts, phase-boundary memory hashes and final full edge histories agree exactly with the author reference. All recorded SDK inputs and metrics reproduce on native re-execution. Three focused tests pass, including an original-kernel golden fixture and restricted pickle loading.

In the 200-node subset, mean weak ties in the middle phase are **44.77** under continuous co-location and **42.01** under remote work, then **44.18 / 43.42** in the final phase. With the full public 501-node demo they are **66.25 / 65.61** during intervention and **68.09 / 67.22** afterward. Each value averages only three seeds and a shortened phase. These small illustrative contrasts should not be presented as replication of the full MIT estimated effect or conclusive policy evidence.

The audit's elapsed time includes all three executions and result writing, excludes the initial source download, and is not a decision-model performance benchmark. Read [verification.json](verification.json) for measured timing, versions, checks and source hashes; [summary.csv](summary.csv) and [trajectories.csv](trajectories.csv) expose world/day results. [The cookbook](../README.md) documents source, adaptation and limits.
