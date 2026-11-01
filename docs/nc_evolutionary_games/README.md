# Evolutionary repeated-game source adapter

The adapter uses the authors' payoff and well-mixed evolution kernels, with archived MTBRQ strategy data. It preserves payoff calculations and declared evolutionary update rules. The archived table is not retrained during these checks.

The source-policy verification includes 972 strategy-pair worlds and 12 population worlds, with 64 members and 50 generations in the latter. Jev can supply strategy decisions through the same environment boundary in a separate transfer experiment. Source notices and provenance remain in the upstream directory.

## Configuration and execution

```bash
python -m examples.nc_evolutionary_games.run --preview
python -m examples.nc_evolutionary_games.run --output runs/my-nc-games
python -m examples.nc_evolutionary_games.export --run runs/my-nc-games --output docs/nc_evolutionary_games/my-results
python -m unittest discover -s tests -p test_nc_evolutionary_games.py -v
```

## Sources and records

- [Evolutionary-game verification results](results/README.md)
- [Source paper](https://doi.org/10.1038/s41467-025-67178-6)
- [Source repository](https://github.com/YuzukiWang/multiagent_q_learning_for_evolutionary_games)
- [plan.json](../../examples/nc_evolutionary_games/plan.json)
- [RepeatedGame](../../examples/nc_evolutionary_games/model.py)
- [WellMixedEvolution](../../examples/nc_evolutionary_games/evolution.py)
- [sources.json](results/sources.json)
- [upstream](../../examples/nc_evolutionary_games/upstream/LICENSE)
