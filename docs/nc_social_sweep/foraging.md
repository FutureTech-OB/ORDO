# Collective foraging and social learning

The native suite contains 18 worlds: four members, 400 physical steps, two map types, three native policies and three seeds. It yields 2,096 policy decisions. Source State, AgentViewGP and navigation semantics are retained, and ORDO yields control only at actual policy-choice boundaries.

Physical time and SDK decision stages are recorded separately. Verification compares source observations, chosen targets, resource collection and group reward. A distinct short Jev pilot changes the choice policy and records its own menu and horizon.

## Configuration and execution

```bash
python -m examples.nc_social_sweep.run_foraging --preview
python -m examples.nc_social_sweep.run_foraging --download --output runs/nc-foraging-local
python -m examples.nc_social_sweep.export_foraging --run runs/nc-foraging-local
```

## Sources and records

- [Adaptive mechanisms of social and asocial learning in immersive collective foraging](https://doi.org/10.1038/s41467-025-58365-6)
- [Source repository](https://github.com/charleywu/minecraftforaging)
- [Native-foraging verification](foraging_results/README.md)
- [Foraging experiment configuration](../../examples/nc_social_sweep/foraging_plan.json)
