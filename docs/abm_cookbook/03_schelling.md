# Schelling segregation

The recipe uses a 12×12 grid, density 0.75, homophily 0.3 or 0.6, 20 rounds and three seeds: six worlds. Happiness is cached at the start of each round. Unsatisfied agents choose an empty destination through the decision interface, while the environment handles occupancy and movement.

The reference comparison uses the same fixed horizon, including periods after all agents become happy, and checks population, positions, happiness and recorded metrics. Destination randomness and source activation semantics are retained.

## Configuration and execution

```bash
python -m examples.abm_cookbook.run --model schelling --output runs/segregation-through-ordo
```

## Sources and records

- [Mesa Schelling segregation example](https://mesa.readthedocs.io/stable/examples/basic/schelling.html)
- [Conventional ABM portability cookbook](README.md)
