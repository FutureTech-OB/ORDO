# Fresh Jev behavioral pilot: protocol

The experiment grid was frozen on 29 October 2026 in plan-before-calls.json before inference. The question is whether collective patterns persist when Jev supplies choices inside published interaction environments.

## Conditions

There are 36 Jev worlds and 36 matched-configuration uniform controls. Spontaneous conventions use N=24, H=5, vocabularies of ten or two, and four worlds each. The stopping criterion is 72 consecutive successful pairs with at least 95% adoption of one name, or 1,000 pairs.

Minority conditions initialize five Q/Q winning memories and fix 0, 4, 5, or 8 members to M, with three worlds each and 1,000 pairs. The final flip criterion requires at least 95% recent-pair success and at least 95% M among non-fixed actions in the last 72 pairs. First attainment is recorded while the run continues to its planned horizon.

Opinion conditions initialize balanced opinions at N=10, 50, and 100, with 3, 10, and 3 worlds respectively. They stop at consensus or t=10, equivalent to 10N asynchronous updates.

## Local inputs and execution

Naming choices use +100/-50 payoffs, five-event personal memories, randomized action ordering, and simultaneous settlement within each pair. Local questions omit population distributions, current opponent choices, and minority counts. The source's 100-round game context is retained with typed probability output.

Opinion choices use other members' opinions, fresh aliases and ordering, randomized k/z mappings, and sequential updates. They have no memory or coordination reward. Jev probabilities are validated and sampled by the SDK. Each relevant event receives a fresh judgment; ready independent questions may share batches of at most 16 with at most four concurrent requests. Plans and logs record inputs, probabilities, sampled choices, payoffs, transitions, seeds, versions, and usage.

Worlds are the replication unit. Analyses report attainment, censoring, final-window behavior, and trajectories. The source comparison records changed engines, output format, sampling policy, and the pilot's selected repetition grid. The later complete twenty-world N=50 configuration has a separate protocol and result record.

## Sources and records

- [Ashery, Aiello & Baronchelli (2025)](https://doi.org/10.1126/sciadv.adu9368)
- [Source repository](https://github.com/Ariel-Flint-Ashery/AI-norms)
- [De Marzo, Castellano & Garcia (2026)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13475478/)
- [Source repository](https://github.com/giordano-demarzo/LLMs-Opinion-Dynamics)
- [replicate_behavior.py](../../examples/llm_abm_cookbook/replicate_behavior.py)
- [behavior.py](../../examples/llm_abm_cookbook/behavior.py)
