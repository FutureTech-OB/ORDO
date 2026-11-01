# Mobility source-kernel adapter

The native suite contains 15 worlds with populations 128 and 1,000, 40 periods and a 300×300 grid, totaling 181,440 source updates. The reference uses the original Windows MSVC/PPL implementation. When memory is disabled, the source's visit counter does not update; the adapter preserves this behavior.

The shared SDK exposes move decisions while the source kernel retains environmental state changes. Full-state checks compare the adapter with direct source execution. Separate Jev pilots explore altered movement judgments and are not combined with these native-policy results.

## Configuration and execution

```bash
python -m examples.ncs_mobility.build --download
python -m examples.ncs_mobility.run --output runs/ncs-mobility-new
python -m unittest discover -s tests -p test_ncs_mobility.py -v
```

## Sources and records

- [Source paper](https://doi.org/10.1038/s43588-021-00160-6)
- [Source repository](https://github.com/tsinghua-fib-lab/Collective-Mobility-Model)
- [Mobility environment construction](../../examples/ncs_mobility/build.py)
- [Mobility model adapter](../../examples/ncs_mobility/model.py)
- [results.json](results.json)
- [results.csv](results.csv)
- [Mobility verification results](results.md)
