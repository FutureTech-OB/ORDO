# Supporting-information audit for the water-resource case

The audit inspects source supporting information for the fields needed to reconstruct agent profiles and decision conditions. Table S5 and linked demographic definitions determine population sampling. Available text and tables do not supply a complete executable original configuration.

The record therefore supports data preparation and interface verification. No new paid model run is attributed to an incompletely reconstructed original population. The commands and source resources below retain the extraction trail.

## Configuration and execution

| Path | Observed results |
|---|---|
| Web-tool navigation to the official attachment | HTTP 403 |
| Standard Python HTTPS request to the official action/downloadSupplement link | HTTP 403 |
| Standard Python HTTPS request to the official doi/suppl/.../supinfo/...docx path | HTTP 403 |
| Article → Supporting Information → S1 in the in-app browser | Article and attachment listings are readable, but publisher verification prevents retrieval of the DOCX supporting information. |
| Targeted public search by DOI, full attachment filename and publisher-linked mirrors | No verifiable supporting-file mirror found |

| Field | Source warm-start requirements | Table S5 verification state |
|---|---|---|
| id | Yes | Original table not retrieved |
| elevated | Yes, retain source Boolean value | Original table not retrieved |
| has_insurance | Yes | Original table not retrieved |
| relocated | Yes | Original table not retrieved |
| trust_in_insurance | Yes, original numbers | Original table not retrieved |
| trust_in_neighbors | Yes, original numbers | Original table not retrieved |
| flood_threshold | Yes, original numbers | Original table not retrieved |
| memory | Yes, complete original wording and order | Original table not retrieved |

## Sources and records

- [Yang & Chiou, WRR 2026, DOI 10.1029/2025WR042111](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2025WR042111)
- [Flood-adaptation study: supporting information (DOCX)](https://agupubs.onlinelibrary.wiley.com/action/downloadSupplement?doi=10.1029%2F2025WR042111&file=2025WR042111-sup-0001-Supporting+Information+SI-S01.docx)
