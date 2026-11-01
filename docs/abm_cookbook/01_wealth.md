# Wealth exchange

This adapter follows the Mesa 3.5.1 Boltzmann wealth example: 60 agents on a 5×5 grid, 15 rounds and three seeds. Movement remains an automatic environmental step; selecting a recipient is the decision event. Agents act sequentially, so later agents observe preceding transfers.

The reference check compares positions, individual balances, random-generator state and Gini trajectories. Total wealth remains 60 and individual balances remain nonnegative. The rule engine supplies the original recipient policy through the same interface available to alternative engines.

## Configuration and execution

```bash
python -m examples.abm_cookbook.run --model wealth --output runs/wealth-through-ordo
```

## Sources and records

- [Mesa Boltzmann wealth model example](https://mesa.readthedocs.io/stable/examples/basic/boltzmann_wealth_model.html)
- [Conventional ABM portability cookbook](README.md)
