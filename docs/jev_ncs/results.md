# Nature Computational Science pilot results

The group runs 14 worlds and 1,839 fresh Jev judgments. In mobility, the history-visible versus hidden return-visit difference is +2.08 and −10.42 percentage points across two seeds. This is an added decision experiment within a mobility environment.

In colocation, remote work changes daily local bridges by −4 and −3.75 relative to continuous colocation; the pilot's bridge count equals its edge count, so structural weak-tie interpretation is limited. Dynamic-network cooperation differences are +46.92 and −32.50 percentage points; the first seed does not actually switch its graph. The recorded pilots exercise decision-policy transfer, while original-kernel checks appear separately.

## Configuration and execution

| Item | Observed value |
|---|---:|
| Worlds | 14: mobility 4, communication 4, dynamic network 6 |
| Valid Jev choices | 1,839: mobility 640, communication 768, dynamic network 431 |
| Within-world updates | 688: mobility 40 periods, communication 48 days, dynamic network 600 focal replacements |
| Global batching stages | 100; batch independent ready questions |
| Requested / returned model | `typesafe/jev-1.14` / `typesafe/jev-1.14-20261014` |
| Successful / attempted requests | 122 / 126; four failed transports including three retries |
| Sum of returned usage.cost | US$0.026123076 |
| Client reserve for failed-request uncertainty | US$0.000842352; metered estimate |
| Total elapsed time across two attempts | 202.560 s, including recovery, analysis and replay; excluding dependency setup and source downloads |

| Seed | Jev: History visible | Jev: History hidden | JevDifference | Difference from matched free-rule configuration |
|---|---:|---:|---:|---:|
| 7 | 0.7292 | 0.7083 | +0.0208 | −0.2917 |
| 11 | 0.5625 | 0.6667 | −0.1042 | −0.4167 |

| Seed | Intervention colocation: mean daily edges | Intervention remote work: mean daily edges | Remote minus colocated | Remote-treatment return: mean daily edges |
|---|---:|---:|---:|---:|
| 7 | 12.25 | 8.25 | −4.00 | 12.00 |
| 11 | 13.50 | 9.75 | −3.75 | 11.50 |

| Seed | Jev: ring Mean cooperation | Jev: star Mean cooperation | Jev: switching Mean cooperation | Switching minus the mean of two static networks | Actual graph switches |
|---|---:|---:|---:|---:|---:|
| 7 | 0.9983 | 0.0600 | 0.9983 | +0.4692 | 0 |
| 11 | 0.6500 | 0.0200 | 0.0100 | −0.3250 | 2 |

## Sources and records

- [README](README.md)
- [verification.json](../jev_validation/coverage.json)
- [analysis.json](../jev_validation/ncs_analysis.json)
- case_results.json: `../../runs/jev-ncs-20261030/case_results.json` (local run artifact)
- [Nature Computational Science pilot configuration (JSON)](../jev_validation/ncs_plan.json)
- [metadata-normalization-recovery.json](../jev_validation/ncs_recovery_metadata.json)
- [Emergence of urban growth patterns from human mobility behavior](https://www.nature.com/articles/s43588-021-00160-6)
- [The effect of co-location on human communication networks](https://www.nature.com/articles/s43588-022-00296-z)
- [Structure-coefficient theorem for evolutionary games on dynamic networks](https://www.nature.com/articles/s43588-026-01068-9)
