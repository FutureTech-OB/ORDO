# Original mobility configuration

This record tracks the original population, grid, horizon and source-kernel build for the mobility model. Native source execution retains exploration, preferential return and memory rules. A Jev decision replacement is a separately declared policy-transfer experiment.

The saved plans and status tables identify completed preparation and execution. They remain separate from the finite native verification suite and from reduced interactive pilots.

## Configuration and execution

| Item | Article / SI evidence | Actual source entry point | Current handling |
|---|---|---|---|
| Population and grid | Main PDF p3 Fig. 2: 30,000 members start centrally; p8 Methods: L300, M30,000 | `main.cpp:37,948`: 300×300, 30,000 members | Fully retained in both configurations |
| Horizon | Main PDF p8: 20,000 periods | `main.cpp:899`: 20,001 moves; period 20,001 writes a state labeled 20,000 before one extra move | Code configuration: 20,001 moves. Paper configuration: 20,000 moves plus a flush-only update/save. |
| Exploration delta | SI PDF p9 / printed p8, S1.5: δ=.1 | `main.cpp:54`: δ=1, not overridden in main | Two independently executed specifications |
| ρ₀ | SI states ρ₀→0; main PDF Fig. 5 p6 and Fig. 6 p7 captions specify ρ₀=0 | `main.cpp:949`: 1e−12 | Paper configuration uses caption-supported zero; code retains 1e−12, with numerical implementation differences explicit |
| Distance parameter | Paper α=.55; distance exponent −(2+α) | `main.cpp:950`: alpha=-2.55 is the already-negative distance exponent | −2.55 in both configurations |
| γ | SI PDF p9: .21 | `main.cpp:57`: .21 | .21 in both configurations |
| Repetitions | SI PDF p18 / printed p17, S6: five seeds | `main.cpp:963`: five runs; `run:884` uses time(0) | Historical seeds unavailable; new declared seeds 2026103000..2026103004 provide reproducible repetitions |
| Other settings | Article describes memory, population feedback and synchronous sampling | History window 1; output window 50; save every 500 periods; visit-array capacity 5,000 | Retained, with explicit capacity-overflow stop |

| Profile | Parameters and total individual updates | Remote directory | PID (rep0..4) |
|---|---|---|---|
| Author code entry point | δ1, ρ₀1e−12, 20,001 moves × 30,000 members × 5 = 3,000,150,000 | `mobility/full-rep-0..4` | 1335598, 1335797, 1335798, 1335799, 1335800 |
| Paper / SI specification | δ.1, ρ₀0, 20,000 moves × 30,000 members × 5 = 3,000,000,000 | `mobility/paper-full-rep-0..4` | 1337350, 1337351, 1337352, 1337353, 1337354 |

```powershell
ssh -oBatchMode=yes -oConnectTimeout=10 anonymousNL 'cat ~/ordo-original-ncs-20261030/mobility/full-rep-0/progress.json'
ssh -oBatchMode=yes -oConnectTimeout=10 anonymousNL 'cat ~/ordo-original-ncs-20261030/mobility/paper-full-rep-0/progress.json'
ssh -oBatchMode=yes -oConnectTimeout=10 anonymousNL 'cd ~/ordo-original-ncs-20261030/mobility && python3 inspect_checkpoint.py paper-full-rep-0/checkpoint.bin'
```

```powershell
ssh -oBatchMode=yes -oConnectTimeout=10 anonymousNL 'cd ~/ordo-original-ncs-20261030/mobility/paper-full-rep-0 && nohup env OMP_NUM_THREADS=4 ../paper-build-v2/cmm_full 2026103000 0 --resume >> stdout.log 2>> stderr.log < /dev/null &'
```

```powershell
python -m examples.ncs_original_mobility.audit --output runs/ncs-original-mobility-20261030/full-candidate-audit.json
```

## Sources and records

- full-original-plan.json: `../../runs/ncs-original-mobility-20261030/full-original-plan.json` (local run artifact)
- [Emergence of urban growth patterns from human mobility behavior](https://www.nature.com/articles/s43588-021-00160-6)
- [Mobility study: author manuscript (PDF)](https://fenglixu.github.io/papers/2021_ncs_emergence.pdf)
- [Mobility study: supplementary information (PDF)](https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs43588-021-00160-6/MediaObjects/43588_2021_160_MOESM1_ESM.pdf)
- [Source repository](https://github.com/tsinghua-fib-lab/Collective-Mobility-Model/tree/21be090028a0b090c6d32675b73ef821893dfaf9)
- [Typesafe Choice API documentation](https://docs.typesafe.ai/primitives/choice)
- [Jev 1.14 model page on OpenRouter](https://openrouter.ai/typesafe/jev-1.14)
