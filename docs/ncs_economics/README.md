# NCS social/economic ABM candidate audit (2026-10-30)

This audit adds **no completed replication**. Nature Computational Science (NCS; DOI prefix `s43588`) is distinct from Nature Communications (NC; `s41467`). Neither candidate below is a review, perspective, research highlight, or the urban CMM paper already covered elsewhere.

## 1. Cumulative reciprocity — preferred ABM candidate, source access blocked

Li, J., Zhao, X., Li, B., Rossetti, C. S. L., Hilbe, C., and Xia, H. (2022). **Evolution of cooperation through cumulative reciprocity.** *Nature Computational Science* **2**, 677–686. Published 20 October 2022. [Official article](https://www.nature.com/articles/s43588-022-00334-w), DOI `10.1038/s43588-022-00334-w`.

This original research combines repeated social-interaction simulations, population strategy evolution, analytical results, and a human economic experiment. Its cumulative-reciprocity strategy tracks the imbalance of past defections. This is a substantive social-cooperation simulation candidate rather than a cellular/biological-model substitute.

The author's [public paper PDF](https://christian-hilbe.github.io/files/2022_li.pdf) states in Code availability (printed page 685; PDF page 9) that Java, MATLAB, and oTree code are available in [Code Ocean archive DOI `10.24433/CO.6894248.v1`](https://doi.org/10.24433/CO.6894248.v1). Reference 57 and the reporting summary confirm the same archive. [Public DataCite metadata](https://api.datacite.org/dois/10.24433/CO.6894248.v1), retrieved 30 October 2026, resolves its actual capsule URL to [0187833/tree/v1](https://codeocean.com/capsule/0187833/tree/v1) and lists MIT and CC0 licenses.

The public DOI redirect returned HTTP 403 from Code Ocean in this environment. No archive files were retrieved, compiled, or executed. The license metadata does not establish the contents or source hashes of files that were not obtained. No source recovery from private accounts, access-control circumvention, or replacement simulation was attempted. This candidate remains **not implemented / not run**.

If the ordinary public archive download becomes accessible, inspect and pin its source first, then identify a bounded population-evolution loop and compare an ORDO adapter against independent execution of that original loop. Do not substitute new code based only on the paper equations and call it an author-kernel replication.

## 2. Dynamic networks — public source obtained, analytical component only

Su, Q., McAvoy, A., and Plotkin, J. B. (2023). **Strategy evolution on dynamic networks.** *Nature Computational Science* **3**, 763–776. Published 11 September 2023. [Official article](https://www.nature.com/articles/s43588-023-00509-z), DOI `10.1038/s43588-023-00509-z`.

The official Code availability statement links the [author's MIT repository](https://github.com/qisu1991/DynamicNetworks), also archived as [Zenodo DOI `10.5281/zenodo.8215243`](https://doi.org/10.5281/zenodo.8215243). The repository was inspected at commit `65bc8a85996bcdd5211845518cf65022d4fe15b1`. Its complete tree contains only `DynamicNetworks.jl`, `README.md`, and `LICENSE`.

`DynamicNetworks.jl` (11,538 bytes; Git blob `700bdb9bc46894cbdddf0d3db790819a32ab764c`) defines reproductive-value, coalescence-time, critical benefit/cost-ratio, and example-network functions. Its top-level examples calculate analytical critical ratios for Figure 2a and the inset of Figure 3a. The file does **not** contain the individual strategy-update/fixation Monte Carlo loop. The README requests Julia 1.5.3 or later plus IterativeSolvers; the official article describes Julia 1.4.1 and MATLAB R2020a.

Running this repository could reproduce a meaningful analytical component of the paper, but would not demonstrate a population ABM executing through ORDO's public decision/environment interfaces. It was therefore **not run or counted as an ABM cookbook replication**, and no new Monte Carlo kernel was written to fill the source gap.

## Counts and evidence boundary

New successful NCS simulation runs from this audit: **0**. New ORDO decisions: **0**. Model API calls: **0**. API cost: **$0**. Existing completed cookbook runs and frozen author-source files were not changed.

These findings support a precise next-step list and demonstrate source screening; they do not add completed-paper coverage, human fidelity evidence, Jev evidence, or new large-scale performance evidence.
