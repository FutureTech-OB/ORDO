# Convention formation, collective bias, and committed minorities

Source: Ashery, Aiello, and Baronchelli (2025), Science Advances 11, eadu9368.

Randomly paired members independently choose a name. Matching earns +100 each; mismatch costs 50 each. Personal memories retain interaction outcomes, allowing conventions to emerge through repeated local encounters. Committed members always choose their assigned name.

ORDO owns pairing and transitions. Both choices are obtained before memories update. N=24 and H=5 are retained; spontaneous vocabulary is Q/M/X/Y/F/J/P/R/C/D and minority vocabulary Q/M. Inputs contain own actions, opponent actions, rewards, and recent scores; population distributions, opponent identity, current opponent choices, and other histories remain outside the input. Population time is pairings/N.

Minority initialization restores five Q/Q wins without inventing missing opponent identities. The archive study contains 27 converged spontaneous runs, six four-member-minority runs, six five-member-minority runs, and 4,500 no-memory responses used as a static preference reference.

## Archive comparison

Recorded actions enter the SDK as one-hot replay choices. All 39 runs match pairings, choices, success, rewards, and final individual dictionaries, including histories and fixed-member flags. Initial convergence filtering and archive coverage define this sample. The archive does not supply original probabilities, reasons, or action-order tokens.

## Organizational extension

The same interaction process supports experiments on shared terminology and work conventions by adding departments, roles, reporting contacts, and access permissions. The thousand-member organizational cookbook provides the implemented extension.

## Sources and records

- [Emergent social conventions and collective bias in LLM populations](https://doi.org/10.1126/sciadv.adu9368)
- [Source repository](https://github.com/Ariel-Flint-Ashery/AI-norms)
- [Source paper](https://doi.org/10.5281/zenodo.14937173)
- [Published LLM social simulations through ORDO](README.md)
- [environments.py](../../examples/llm_abm_cookbook/environments.py)
- [run.py](../../examples/llm_abm_cookbook/run.py)
