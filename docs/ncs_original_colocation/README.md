# Original colocation configuration records

This directory records preparation and execution state for the source organizational-colocation model. The model links physical presence with communication contacts and local bridges. Source schedules, populations, network construction and observation timing must be retained for original-condition comparisons.

The saved configuration, source links and run-status records below identify the actual execution scope. Reduced Jev pilots and native-source checks are separate experiments. This release does not launch additional remote runs.

## Configuration and execution

| Item | MIT study in the article | Public source capsule code |
| --- | --- | --- |
| Population data | 2,834 MIT faculty/postdocs; autumn analysis filters to 2,206 | Graph file: 500 nodes; distances: 501 IDs; historical candidate edges: 436 endpoints |
| Candidate edges | Edges appearing at least once in the empirical history E; complete E, mail and pairwise distances are private | All 1,577 public weekday historical edges retained |
| Stage-1 count | ε₁∼N(1000,10) | **50+int(shift)**, shift∼N(0,3) |
| Stage-2 count | ε₂∼N(500,10) | **20+int(shared shift)**; both stages share daily noise |
| Contact-weight parameters | P=80,000; N=2,000; O=1; D=90,000; F=200,000 | Same: Cₚ=2/3, Cₙ=2, Cₒ=1, Cᴅ=10/11, Cꜰ=2/3; other add/distance weights zero |
| Time and status | Two network stages per day before advancing the day | Complete source stages, global sampling without replacement and memory updates are retained, without reduced active sets or shortened daily phases. |

| Stage | Source start→end indices, right endpoint excluded | Native simulation days |
| --- | --- | ---: |
| Shared colocation prefix | 10→62 | 52 |
| Remote work | 62→439 | 377 |
| Return to colocation | 439→477 | 38 |
| Distance-preserving counterfactual branched from prefix memory | 62→477 | 415 |
| Total actual execution | Two complete 467-day paths share a 52-day prefix | **882** |

```powershell
$env:PYTHONPATH = '.deps;.buildtmp/behavior-plot-deps;.buildtmp/nc-social-deps'
python -m examples.ncs_original_colocation.run_native --output runs/ncs-original-colocation-local
```

```powershell
python -m examples.ncs_original_colocation.run_jev --preview --output runs/ncs-original-colocation-20261030/jev
```

```powershell
python -m examples.ncs_original_colocation.run_jev --allow-paid --max-cost-usd 0.05 --batch-size 512 --concurrency 4 --output runs/ncs-original-colocation-20261030/jev
```

```powershell
python -m examples.ncs_original_colocation.run_jev --allow-paid --resume --max-cost-usd 50 --batch-size 512 --concurrency 4 --output runs/ncs-original-colocation-20261030/jev
```

## Sources and records

- [The effect of co-location on human communication networks](https://www.nature.com/articles/s43588-022-00296-z)
- [Code Ocean DOI](https://doi.org/10.24433/CO.5754680.v1)
- [Colocation study: author code on Code Ocean](https://git.codeocean.com/capsule-8904315.git)
- [Supplementary Information](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs43588-022-00296-z/MediaObjects/43588_2022_296_MOESM1_ESM.pdf)
- [Colocation study: public representative dataset on Zenodo](https://zenodo.org/records/6809296)
- Recorded experiment configuration: `../../runs/ncs-original-colocation-20261030/plan-before-run.json` (local run artifact)
- Verification report: `../../runs/ncs-original-colocation-20261030/verification.json` (local run artifact)
- Daily outcome metrics: `../../runs/ncs-original-colocation-20261030/daily_metrics.csv` (local run artifact)
- Verification report: `../../runs/ncs-original-colocation-20261030/staged-native-check/verification.json` (local run artifact)
