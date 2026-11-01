# Network polarization with Jev and conditional DeepSeek content

Source: Piao et al., Emergence of polarization in networks of large language model agents, Nature Communications (2026). The author MIT repository is pinned to 7bc447f6d470aa232f93de5dabaa4c87fc4414d9.

## Current configuration

The Gun Control baseline contains 1,000 members, 4,000 initial directed links, and forty planned epochs. Eleven epochs are complete. Jev (typesafe/jev-1.14) chooses stance, whether to retain a contact, and whether to speak; deepseek/deepseek-v4.1-flash-1017 generates conditional reasons and posts with temperature one and reasoning effort low. Preflight receipts record reasoning tokens. Client allowances are $10 for Jev and $40 for content.

The execution records five-level opinion distributions, neutrality, mean and absolute opinion, homophilic edges, link changes, speech and message counts, and provider costs. Returned judgments in the recorded period total 68,161. The current frozen plan, progress, and accounting are included in the appendix evidence directory.

## Interaction stages

The source propagation loop supplies visible posts. Jev selects a stance and the content model generates a reason conditional on that stance. Jev then evaluates active members' outgoing links, with source-rule random reconnection. A speech decision for each target precedes a newly generated persuasive post. Messages and reasons affect subsequent decisions.

## Source adaptations

Initialization uses the author epoch-zero network and opinions with newly generated reasons and seed posts for about 10% of members. The original public entry point defaults to 2,000 people and 2,000 epochs; this arm explicitly selects the main-figure 1,000-member, forty-epoch baseline. Source patience is initialized to zero. Iteration order is deterministic.

The adapter retains source -0 indexing, sequential propagation, target=0 handling, and duplicate outgoing links. The author persuasion function overwrites intermediate calls; this adapter generates the last effective prompt. Choice and content are separated into the two providers. Protocol tests compare propagation and local inputs.

## Technical execution record

The saved status is failed after a Missing generated content response during epoch twelve. Its invalid content record requires recovery handling before this saved run can resume. Successful-response usage and uncertain-attempt reservations are recorded separately. The analysis entry point compares trajectories, endpoint opinion distributions, RMSE, direction, and both cost categories after completion. Paid execution requires OPENROUTER_API_KEY and explicit allowances.

Organizational extensions can distinguish departmental, cross-departmental, and reporting contacts and enforce information permissions.

## Configuration and execution

```bash
python -m examples.nc_polarization_live.run --preview --download --output runs/NEW
python -m examples.nc_polarization_live.run --allow-paid --output runs/NEW --reasoning low
# Resume runs with valid saved responses; repair invalid response content first:
python -m examples.nc_polarization_live.run --allow-paid --resume --output runs/NEW --reasoning low
# Read later author trajectories only after execution, for comparison:
python -m examples.nc_polarization_live.analyze --run runs/NEW
python -m unittest discover -s tests -p test_nc_polarization_live.py -v
```

## Sources and records

- [Piao et al., Emergence of polarization in networks of large language model agents](https://www.nature.com/articles/s41467-026-78228-y)
- [Source repository](https://github.com/tsinghua-fib-lab/LLM_for_Polarization/tree/7bc447f6d470aa232f93de5dabaa4c87fc4414d9)
- [Verification report (JSON)](../appendix_ordo_v2_evidence/polarization-partial/verification.json)
- [Recorded experiment configuration (JSON)](../appendix_ordo_v2_evidence/polarization-partial/plan-before-calls.json)
- [Recorded execution progress (JSON)](../appendix_ordo_v2_evidence/polarization-partial/progress.json)
- Simulation trajectory: `../../runs/nc-polarization-hybrid-20261030/trajectory.json` (local run artifact)
- [Verification report (JSON)](../appendix_ordo_v2_evidence/polarization-partial/verification.json)
- Verification report: `../../runs/nc-polarization-hybrid-preflight-20261030/verification.json` (local run artifact)
- [Network-polarization interaction protocol](../../examples/nc_polarization_live/protocol.py)
- [Network-polarization content generation](../../examples/nc_polarization_live/content.py)
- [Network-polarization execution entry point](../../examples/nc_polarization_live/run.py)
