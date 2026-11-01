# Repeated games: raw-probability sampling results

Recorded on 30 October 2026. The complete 64-pair, twenty-round source tournament returns 320 Jev choices: 81 cooperative actions (25.31%) and 239 defections. The author GPT-4 archive contains 204 cooperative actions out of 320 (63.75%).

Raw cooperation probabilities range from 0.04 to 0.98 and average 0.2503. Provider-reported cost is $0.01111475 and execution with verification takes 341.0 seconds.

All 320 SDK probabilities match provider responses. Prompt, author-loop feedback, and complete saved-trajectory checks pass. This is a fresh sampling arm with new judgments along its resulting histories. The earlier argmax tournament has zero cooperative choices and is retained separately. Opponent-level trajectories report cooperation, reciprocity, and retaliation.

## Sources and records

- [Repeated-game sampled results (JSON)](nhb_sampled_results.json)
- [Repeated-game match results (CSV)](nhb_sampled_matches.csv)
- [Verification report (JSON)](../appendix_ordo_v2_evidence/games/verification.json)
- [Repeated games: historical argmax arm](nhb_results.md)
