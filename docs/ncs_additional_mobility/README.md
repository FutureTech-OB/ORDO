# PedNav: an author-native navigation component from Nature Computational Science

This cookbook executes the two published pedestrian route generators on the authors' Boston street graph and public origin/destination sample. It demonstrates that ORDO can wrap an existing human behavior component through `describe -> prepare -> FunctionEngine -> advance`, without rewriting its numerical mechanism. Each SDK action commits one independent route. These trips do not interact or change their environment: this is a behavioral component integration, **not a coupled social ABM**, an organization experiment, or a new Jev evaluation.

Source: Bongiorno et al., [Vector-based pedestrian navigation in cities](https://www.nature.com/articles/s43588-021-00130-y), *Nature Computational Science* 1, 678–685 (2021), original research article, DOI `10.1038/s43588-021-00130-y`. Author [PedNav repository](https://github.com/cbongiorno/pednav), fixed commit `8aa7bb147dcd9e7b3b3bb3183cae6b583cca4980`; [archived code release](https://doi.org/10.5281/zenodo.5187718).

## Run from the repository root

Install the optional dependency into your chosen Python environment. NumPy is already a base project dependency.

```powershell
python -m pip install igraph==0.11.9
python -m examples.ncs_additional_mobility.run --download --trip-limit 100 --output runs/pednav-my-run
python -m examples.ncs_additional_mobility.verify runs/pednav-my-run
python -m unittest discover -s tests -p test_ncs_additional_mobility.py -v
```

The output directory must be new. The first command with `--download` fetches about 50 MB of publicly released author code/data into ignored `.buildtmp/ncs-pednav-sources`, with exact file sizes, fixed Git blob hashes and SHA256 recorded. Later runs can omit `--download`. The unmodified `Navigation` class is extracted from the pinned author module; the authors' two numerical functions are invoked directly. The original module-level NumPy error-policy side effect is replaced by a scoped context. Explicit per-trip seeds are set and restored. Pickle constructors are restricted to the verified NumPy/igraph types needed by these pinned graph files; arbitrary archive constructors and persistent references are rejected.

The default is 20 public trips, two mechanisms (`vector`, `shortest`), two noise values (`0.0`, `0.7`) and three seeds (`7`, `11`, `17`). `--trip-limit 100` uses all 100 public OD pairs. For a custom sweep, copy `cases.json` from the run, edit the values and pass `--cases path/to/cases.json`. The configured `sigma=0.7` is illustrative, not a newly estimated human fit.

## What is checked and exported

- Author graph: 78,402 vertices, 112,527 undirected edges; original edge lengths in meters.
- Reference: independently invoke `Stochastic_Vector_Path` / `Stochastic_Shortest_Path` directly on each OD pair under the same explicit seed. Compare **every node of every resulting path** with ORDO. The reference bypasses the SDK and wrapper's `route()` method; this checks the adapter, not the underlying scientific validity of the author's functions.
- Verify route endpoints, every traversed original edge, length and distance-relative detour. NumPy RNG state restoration is also unit-tested.
- `verification.json`: configurations, exact-match results, environment versions, controller counts, elapsed times, source hashes and output hashes.
- `world-*/generated_routes.json.gz`: fresh generated paths, not archived human trajectories substituted as simulation outputs.
- `world-*/ordo/events.jsonl` and `result.json`: SDK scheduling and audit records.
- `world-*/native-reference.json`: independently produced reference digest and timing.
- `routes.csv`: per-trip endpoints, length, shortest distance, detour ratio and path digest.

The small public human sample supplies OD pairs only. No human-model goodness-of-fit test is performed. The full GPS dataset is not released here, and we do not reproduce the paper's complete cross-city prediction analysis, fit its parameters, or claim its reported predictive improvement. Mechanism portability and native path equality are the supported conclusions. Timing is a local implementation observation and includes metrics/export in ORDO; it is not an LLM speed comparison.

## Provenance and licensing

The author repository is GPL-3.0; its exact license is downloaded and preserved alongside the sources. No author numerical code or graph pickle is copied into this cookbook's committed source tree. A downloader and adapter do not change the author's license. Redistribution of an integrated package must retain applicable notices and comply with that license; these files do not relicense the upstream work. The paper describes street networks obtained from OpenStreetMap; retain [OpenStreetMap attribution](https://www.openstreetmap.org/copyright) and its data terms when redistributing derived graph data. Public GPS-derived sample trajectories remain subject to their source release terms; this cookbook uses the public fixed release and does not fetch private individual data.

The original `pednav/main.py` SHA256 is `e98a77e2b8de2e2963f377a96a3e53b54c6daa52fd524f73f9a5dd11530caf16`. Boston graph SHA256 is `dd10bad05fb16bfe703de432685c8f12cab537d7fe5771945678081d6a4f89a4`; public paths SHA256 is `a6ecb65ea8d59670e730a13f82cf903dc4fd2a1b51de86eb12cb7df92c7db031`. Full fixed URLs, sizes and hashes appear in `source_manifest.json`.

## Why this is useful for ORDO

A future organizational simulation may need an external route/mobility component, for example employees moving between facilities. This integration provides a reusable example of wrapping an existing published behavior model and auditing it independently. Such an organizational extension has **not** been implemented or validated by this cookbook.
