# Offline review evidence

Exported synthetic experiment records for the v2 technical appendix. The manifest lists hashes of compressed and original bytes. No API credentials are included.

`naming/` includes a shared provider journal also containing the older opinion pilot; its provider cost must not be assigned to the naming experiment alone. `majority/` is the newer twenty-world condition. `games/` is the raw-probability sampling run. `polarization-partial/` records an interrupted run and is not a completed forty-epoch result.

From the repository root, run `python tools/replay_ordo_v2_review.py` to verify all exported bytes and replay the three completed cases without model API calls. The NHB replay requires the pinned public author source cache; see the appendix for its free download command.
