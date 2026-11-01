# Science Advances pilot results

The group runs 16 worlds and 1,676 fresh Jev judgments. In the short naming-game pilot, six worlds with 96 pairs each do not establish a convention; the separate longer run reaches the criterion in 8/8 spontaneous worlds. Majority coordination reaches consensus in 2/4 worlds, with other endpoints 0.90 and 0.92.

In the public-goods adaptation, final cooperation is 52.5% on the high-return star, versus zero in the low-return star and complete graph. Of eight high-return groups, four become all-cooperative, two all-defecting and two remain mixed. This directional pilot has a finite horizon and is separate from the source's weak-selection fixation analysis. Complete numeric and protocol tables follow.

## Configuration and execution

| Paper | New case | Fresh judgments | Assessment |
| --- | ---: | ---: | --- |
| Ashery et al. 2025: conventions and committed minorities | 6 | 1,021 | **Not observed**: no strong coordination or minority transition within 96 pairs |
| De Marzo et al. 2026: majority influence and coordination | 4 | 560 | **Partial support**: coordination increases; 2/4 worlds reach consensus |
| Wang & Su 2026: structured public goods | 6, containing 24 independent colonies | 95 | **Directional support**: star r=6 exceeds star r=3 and complete r=6 in both seeds |

| Committed M members | Seed | Last-72-pair coordination | Ordinary-member latest M share at endpoint | High-coordination criterion |
| ---: | ---: | ---: | ---: | --- |
| 0 | 7 | 50.0% | 54.2% | No |
| 0 | 19 | 51.4% | 29.2% | No |
| 4 | 7 | 69.4% | 5.0% (1/20) | No |
| 4 | 19 | 69.4% | 0.0% (0/20) | No |
| 5 | 7 | 59.7% | 0.0% (0/19) | No |
| 5 | 19 | 65.3% | 10.5% (2/19) | No |

| Population | Seed | Asynchronous updates | Final coordination | First consensus within window |
| ---: | ---: | ---: | ---: | --- |
| 20 | 7 | 80 | 0.90 | Not observed |
| 20 | 19 | 80 | 1.00 | Update 65 (t=3.25) |
| 50 | 7 | 200 | 1.00 | Update 198 (t=3.96) |
| 50 | 19 | 200 | 0.92 | Not observed |

| Network and synergy | Seed 7: four colony endpoint cooperation shares | Seed 19: four colony endpoint cooperation shares | Mean across all eight colonies | All-cooperate / all-defect / mixed |
| --- | --- | --- | ---: | --- |
| Star, r=3 | 0, 0, 0, 0 | 0, 0, 0, 0 | 0.000 | 0 / 8 / 0 |
| Star, r=6 | 1, 0.1, 0.1, 0 | 0, 1, 1, 1 | **0.525** | 4 / 2 / 2 |
| Complete graph, r=6 | 0, 0, 0, 0 | 0, 0, 0, 0 | 0.000 | 0 / 8 / 0 |

| attempt | Network attempts | Saved successful responses | Reported successful-response cost |
| --- | ---: | ---: | ---: |
| 1, interrupted | 145 | 140 | $0.018616668 |
| 2, completed after log recovery | 60 | 60 | $0.002224782 |
| Total | **205** | **200** | **$0.020841450** |

## Sources and records

- [Fresh Jev pilots in three Science Advances interaction protocols](README.md)
- [verification.json](../jev_validation/coverage.json)
- [analysis.json](../jev_validation/sa_analysis.json)
- Per-case results: `../../runs/jev-sa-20261030/case_results.json` (local run artifact)
- [Emergent social conventions and collective bias in LLM populations](https://www.science.org/doi/10.1126/sciadv.adu9368)
- [Convention formation and committed minorities: results](../llm_abm_cookbook/behavior_results/README.md)
- [AI agents can coordinate via majority-following beyond human scale](https://www.science.org/doi/10.1126/sciadv.aea6091)
- [Public goods games on any population structure](https://www.science.org/doi/10.1126/sciadv.aeb1263)
- [Public goods games on any population structure — full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965315/)
