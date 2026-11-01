# Source provenance

Source paper: Barkoczi, D., & Galesic, M. (2016). Social learning strategies modify the effect of network structure on group performance. *Nature Communications*, 7, 13109. https://doi.org/10.1038/ncomms13109

Author code: https://github.com/dnlbrkc/social_learning

Inspected commit: `93b5f6fb18290ff67a5a676c9ef98a5aa3165f71`.

The prior project inspected `simulation_NK.R`, `simulation_MW.R`, `landscapes/generate_NK.R` and the README. No downloaded R code was executed. These upstream files are not redistributed in this repository. No license is assumed for them and no license is applied to them by this project.

`orgabm/kernel.py` is adapted from this project's existing `policy_abm.py`, whose frozen pilot SHA-256 is `c57621c7b85e0bfd3745a24937cd7091556ecaed631f472ca9dcdbb54cc15075`. The changes here replace local import paths and allow externally supplied observed contacts at transition time. The original pilot files were left untouched.

`examples/archived_pilot.json` is a compact export of this project's 2026-10-15 completed Jev policy pilot. It includes SHA-256 fingerprints of the original summary, configuration and checkpoint, all world-level metric trajectories and the original audit summary. It does not contain API credentials. It is not a new model run and does not evaluate the newly added organization modules.

The export can be rebuilt with `python tools/build_archive.py PATH_TO_ORIGINAL_PILOT_DIRECTORY`. Full raw API records from the original pilot remain outside this compact draft. Submission packaging must add an accessible raw archive or a sufficiently complete equivalent research object.
