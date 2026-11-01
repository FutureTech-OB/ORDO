# Additional Nature Communications game adapters

These source-kernel adapters cover repeated-game and reputation mechanisms. Decisions pass through the common environment interface; payoffs, histories and population transitions preserve the declared source equations. Source versions, conditions and commands are retained below.

The native-reference checks exercise rule-policy equivalence. Fresh Jev transfer pilots are recorded separately, with their action menus and horizons.

## Configuration and execution

```bash
python -m examples.nc_additional_games.run --preview
python -m examples.nc_additional_games.run --output runs/my-social-rewarding
python -m examples.nc_additional_games.export --run runs/my-social-rewarding --output docs/nc_additional_games/my-results
python -m unittest discover -s tests -p test_nc_additional_games.py -v
```

## Sources and records

- [Additional-game verification results](results/README.md)
- [Pal & Hilbe (2022), Reputation effects drive the joint evolution of cooperation and social rewarding, Nature Communications 13:5928](https://doi.org/10.1038/s41467-022-33551-y)
- [Source repository](https://github.com/Saptarshi07/social-rewarding)
- [plan.json](../../examples/nc_additional_games/plan.json)
- [SocialRewarding](../../examples/nc_additional_games/model.py)
- [sources.json](results/sources.json)
- [upstream](../../examples/nc_additional_games/upstream/LICENSE)
