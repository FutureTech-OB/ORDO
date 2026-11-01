# Nature Communications interaction adapters

The collection ports social-reward and collective-foraging source environments to ORDO. Each adapter specifies which local choice is exposed to a decision engine, which dynamics remain environmental, and how time and state checks map to the source implementation. Native-rule verification and new Jev judgments have separate records.

The social-reward native suite has 18 worlds with 100 members and 3,000 updates each: 54,000 source updates. It checks the finite source trajectory rather than the paper's much longer steady-state calculation. Collective foraging uses its source view and navigation code, with physical movement between policy-choice events.

## Configuration and execution

```bash
python -m examples.nc_social_sweep.run --preview
python -m examples.nc_social_sweep.run --download --output runs/nc-social-local
python -m examples.nc_social_sweep.export --run runs/nc-social-local
python -m unittest discover -s tests -p test_nc_social_sweep.py -v
```

## Sources and records

- [Collective foraging and social learning](foraging.md)
- [Universality, criticality and complexity of information propagation on social media](https://doi.org/10.1038/s41467-022-28964-8)
- [Social-reward source verification](results/README.md)
- [plan.json](../../examples/nc_social_sweep/plan.json)
- [SocialActivation](../../examples/nc_social_sweep/model.py)
- [Social-interaction source retrieval](../../examples/nc_social_sweep/sources.py)
