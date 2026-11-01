# Water Resources Research source audit

The source study uses demographic and contextual information for interacting water-resource choices. Reconstructing the original population requires the supporting-information demographic distribution, including Table S5. This source audit identifies missing inputs before a paid behavioral run.

The current implementation provides an offline environment and interface check. The original population has not been reconstructed from incomplete demographic information. Source files, supporting-information references and extraction commands are retained below.

## Configuration and execution

| Configuration name | Initialization | Flood | Preparation state |
|---|---|---|---|
| Default source branch without CSV input | Source-generated randomness | Annual flood probability 0.2 | Reviewed; no additional run started |
| Paper-described profiles | Insurance trust U(.3,.6), neighbor trust U(.4,.65), randomized initial elevation | 3/4/9 years specified in Figure 2 | Differs from source code; missing values are not invented |
| **This run: `build_cases()`** | **Original source generator with newly declared seeds** | **3/4/9 years in Figure 2** | **50 independent worlds × 100 households × 10 years**, prepared |

| Source field | Source distributions / initial values |
|---|---|
| id | Agent_1..Agent_100 |
| elevated / relocated | All False |
| has_insurance | Random True/False choice |
| memory | Randomly select two or three of the five source historical-event sentences |
| trust_in_insurance | U(.2,.5), rounded to two decimals |
| trust_in_neighbors | U(.35,.55), rounded to two decimals |
| flood_threshold | U(.4,.9), rounded to two decimals |
| intends_to_adapt | None |
| Annual actions, two appraisals and flood_history | Empty list |

```powershell
python -m examples.llm_wrr_original.run --preview --output runs/llm-wrr-original-20261030
python -m unittest examples.llm_wrr_original.test_mechanics -v
```

```powershell
python -m examples.llm_wrr_original.run --allow-paid --output runs/llm-wrr-original-20261030 --max-cost-usd 5 --batch-size 64 --concurrency 4
```

## Sources and records

- [Yang & Chiou, *Water Resources Research* 62(6), e2025WR042111 (2026)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2025WR042111)
- [Source repository](https://github.com/ethanyang28/LLM_ABM_Flood/tree/6952c793b3b3c0b0c0adfabc6e34062146d351da)
- [wrr_mechanics_verification.json](wrr_mechanics_verification.json)
- [Flood-adaptation configuration preview (JSON)](wrr_preview.json)
