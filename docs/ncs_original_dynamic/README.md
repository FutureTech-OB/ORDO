# Dynamic-network original configuration

The source environment combines evolutionary decisions with a declared network-switching process. Configuration records retain graph files, population, generation count, update order and the source structural conditions. Switching events are recorded explicitly so a strategy change is not automatically attributed to a network change.

Saved plans, source resources and actual execution status follow below. The release retains the historical run state without starting new paid or remote work.

## Configuration and execution

| Evidence location | Verified items | Current handling |
|---|---|---|
| [Figure 3 caption and diagram](https://www.nature.com/articles/s43588-026-01068-9/figures/3) | An even-sized core ring with disconnected peripheral nodes; each layer connects the periphery to one contiguous half of the core. | Reconstructed from published diagrams and labeled `published_caption_reconstruction` |
| Figure 3 main results | Nc10, Np60, μ.01, δ.005; representative τ10 for cooperation/fairness and τ.1 for altruism/trust | Analytical structural-coefficient calculation, separate from a completed Monte Carlo grid |
| Figure 3 plotting script | Duration exponent −1:.04:3; mutation exponent −3:.03:0 with panel-specific endpoint omissions; peripheral data 2:80, plotted subset; several scripts set δ.0025 | Plot scripts differ from the official δ.005 caption; the discrepancy is retained and configurations are kept separate |
| [Figure 4](https://www.nature.com/articles/s43588-026-01068-9/figures/4) | Illustrative invasion/resistance trajectory at Nc4, Np10 | No archived Figure 4 generation workflow; the 105-step illustration is separate from steady-state analysis |
| [Extended Data Figure 2 caption](https://www.nature.com/articles/s43588-026-01068-9#Fig7) | Nc8, τ1, μ.05; δ.01/.1/.5; donation b2,c1; 10 repetitions per point, 10^8 events each | All listed parameters and repetitions retained |
| Author-data horizontal axis | Np100, 110, 120, 130, 140, 150, 160 | All seven values enter the queue |
| Original`Simulation.jl` | Draw focal/death, then birth from all positive-weight neighbors; copy, mutate, switch network and update payoffs; discard first 5% | Statement-level source execution with original timing, full candidate set and 5,000,000-step burn-in |
| Author README | Full large-scale figure drivers unavailable; archive contains generic kernel, minimal demo, plots and precomputed results | Graph construction, parameter scheduling and logging are documented local reconstructions |

| Structure | Complete repetitions | New-run mean cooperation | Between-world SE | Archived author value | New minus archived |
|---|---:|---:|---:|---:|---:|
| dynamic | 10×10^8 | 0.0892108021 | 0.0001992070 | 0.0899604785 | −0.0007496765 |
| static | 10×10^8 | 0.0726970908 | 0.0001382401 | 0.0728859363 | −0.0001888455 |

```text
/home/anonymous/ordo-original-ncs-20261030/dynamic/
```

```text
/home/anonymous/ordo-original-ncs-20261030/dynamic/native-donation-full-grid/
```

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 anonymousNL "cat /home/anonymous/ordo-original-ncs-20261030/dynamic/native-donation-full-grid/status.json"
ssh -o BatchMode=yes -o ConnectTimeout=10 anonymousNL "python3 /home/anonymous/ordo-original-ncs-20261030/dynamic/collect_results.py /home/anonymous/ordo-original-ncs-20261030/dynamic/native-donation-full-grid"
```

## Sources and records

- [Zhang et al. (2026), Structure-coefficient theorem for evolutionary games on dynamic networks](https://www.nature.com/articles/s43588-026-01068-9)
- [Zenodo22152088](https://doi.org/10.5281/zenodo.22152088)
- [Dynamic-network study: Figure 3 and caption](https://www.nature.com/articles/s43588-026-01068-9/figures/3)
- [Dynamic-network study: Figure 4 and caption](https://www.nature.com/articles/s43588-026-01068-9/figures/4)
- [Dynamic-network study: Extended Data Figure 2](https://www.nature.com/articles/s43588-026-01068-9#Fig7)
- [Dynamic-network study: supplementary information (PDF)](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs43588-026-01068-9/MediaObjects/43588_2026_1068_MOESM1_ESM.pdf)
- Verification snapshot: `../../runs/ncs-original-dynamic-20261030/verification.snapshot.json` (local run artifact)
- Experiment configuration: `../../runs/ncs-original-dynamic-20261030/plan.json` (local run artifact)
- Launch record: `../../runs/ncs-original-dynamic-20261030/launch.json` (local run artifact)
- Execution status: `../../runs/ncs-original-dynamic-20261030/status.json` (local run artifact)
- Independent-run records: `../../runs/ncs-original-dynamic-20261030/repeats/` (local run artifact)
- [Dynamic-network source manifest](../../examples/ncs_original_dynamic/sources.json)
- [launch_remote.py](../../examples/ncs_original_dynamic/launch_remote.py)
- [Dynamic-network environment implementation](../../examples/ncs_original_dynamic/environment.py)
