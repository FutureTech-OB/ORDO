# Majority influence and population coordination

Source: De Marzo, Castellano, and Garcia (2026), Science Advances 12, eaea6091.

One randomly selected member updates a binary opinion after observing the other members. The choice changes the population encountered by the next actor. Initial opinions are balanced; there is no memory, coordination reward, or instruction to follow the majority. Each event uses fresh randomized aliases, ordering, and a randomized mapping between k/z and underlying opinions. Time increments by 1/N; magnetization is m=(N+ - N-)/N and coordination is abs(m).

The adapter retains individual identities for organizational extension while using random single-member activation. Typed action probabilities replace source text-output parsing.

## Author data checks

Five fully_connected_50 files contain 3,064 rows for Claude Haiku, Claude Opus, GPT-3.5, GPT-4 Turbo, and Llama-3-70B. Checks reconstruct integer population counts, consecutive within-segment time, and single-update changes of at most 2/N. The GPT-4 file includes resets and a duplicated step 270; export keeps six zero-start segments and an overlapping segment starting at 270.

The author writes observations before updates. Group magnetization supports aggregate trajectory checks. Individual actors and sampled actions are absent from those files. Ten-model adoption references contain 150 rows; five reported fractions differ from count ratios and are preserved with discrepancy records.

## Interfaces and fresh execution

Jev and optional chat serializers were initially checked using mocked HTTP responses. Fresh inference is documented in the later behavioral pilot and complete twenty-world N=50 run. Sequential updates retain their causal dependencies; batching spans independent worlds. Comparisons measure trajectories, consensus times, final distributions, engine usage, and costs.

## Sources and records

- [AI agents can coordinate via majority-following beyond human scale](https://doi.org/10.1126/sciadv.aea6091)
- [Source repository](https://github.com/giordano-demarzo/LLMs-Opinion-Dynamics)
- [Source paper](https://doi.org/10.5281/zenodo.17911594)
- [MajorityOpinion](../../examples/llm_abm_cookbook/environments.py)
- [Archived LLM-simulation verification](verified_results.md)
