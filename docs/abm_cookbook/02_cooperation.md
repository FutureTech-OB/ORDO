# Spatial cooperation

The spatial prisoner's dilemma uses a 12×12 grid, 20 rounds, temptation values 1.2 and 1.8, and Simultaneous, Sequential and Random activation. Seeds 7, 8 and 9 produce 18 worlds. The adapter preserves the reference's cumulative score and first-maximum tie handling.

The decision event selects whose strategy to copy. The environment computes interactions and commits strategy changes in the source activation order. Reference checks compare strategies, scores and trajectories for every declared condition.

## Configuration and execution

```bash
python -m examples.abm_cookbook.run --model cooperation --output runs/cooperation-through-ordo
```

## Sources and records

- [Mesa spatial prisoner's dilemma example](https://mesa.readthedocs.io/stable/examples/advanced/pd_grid.html)
- [Conventional ABM portability cookbook](README.md)
