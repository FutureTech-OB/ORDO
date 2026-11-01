# Repeated games: the source SI B.2 tournament

Source: Akata et al., Playing repeated games with large language models, Nature Human Behaviour 9, 1380-1390 (2025). The implemented condition is the full SI B.2 Tit-for-tats source tournament, with twenty rounds per ordered pair.

The MIT author repository is pinned to 224a605a21127cac69763f990e077f7b05abd422. Script pd/tft/pd_base_gpt4_tfts_query.py has blob 63badbcf8288b6cc7326a4d32866d3655c7a3253 and 7,833 bytes; the archived CSV has blob a25bf44cac213bb4ea2d19d23aad8f9a7341d201 and 44,713 bytes. File bytes and license are checked before selected AST definitions are loaded.

## Players, feedback, and sampling

The eight ordered roles are GPT4, TFT, TFTT, STFT, RTFT, HTFT, NP10, and NP20. All 8x8=64 ordered pairs run for twenty rounds: 1,280 game rounds and 2,560 player actions. Jev substitutes for GPT4 in fifteen matches, including self-play, producing 320 fresh model choices in 300 SDK stages. The other 49 matches use rules. J denotes cooperation and F defection; payoffs are JJ=(8,8), JF=(0,10), FJ=(10,0), and FF=(5,5).

Both players decide before round history updates. Seven rule functions come from the author AST. HTFT's first action is F in the source, and prev/prev2/prev3 carry across matches; these behaviors are retained. NP strategies use declared seed 20261030 because the author's random seed was unpublished.

The default policy samples raw provider probabilities with no application temperature rescaling. The source GPT-4 settings (gpt-4-0613, temperature zero, one output token) remain source metadata. Argmax is a separate historical arm. All provider probabilities and sampled actions are recorded.

## Execution and checks

The runner freezes the plan before calls and supports exact-event recovery with unchanged configuration, source, and allowances. Defaults cap client cost at $0.20 and attempts at 1,000. Outputs include plans, receipts, SDK events, all source transition rows, case results, analysis, and verification.

Protocol checks compare all 1,280 transition rows with an independent author outer loop, verify prompts and feedback, exercise changes in J/F choices and invalid submissions, and replay sampled actions. The archived CSV is used for endpoint comparison. The paid arm's results are documented separately.

## Configuration and execution

```powershell
python -m examples.llm_nhb_original.sources --download
python -m unittest examples.llm_nhb_original.test_protocol -v
python -m examples.llm_nhb_original.run --preview --output runs/NEW
```

```powershell
python -m examples.llm_nhb_original.run --allow-paid --action-policy sample --max-cost-usd .20 --output runs/NEW
```

## Sources and records

- [Akata et al., Playing repeated games with large language models](https://www.nature.com/articles/s41562-025-02172-y)
- [eliaka/repeatedgames](https://github.com/eliaka/repeatedgames)
