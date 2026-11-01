"""Write reproducible, strictly offline source-loop compatibility evidence."""
import hashlib
import json
from pathlib import Path

from .environment import SOURCE, UPSTREAM, native_reference
from .test_mechanics import chooser, run_adapter


def main():
    records = []
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    for seed in (0, 1, 7, 19, 20261030, 20261079, 20261100, 982, 233):
        for mode in ('inaction','relocate','elevate','mixed'):
            choose = chooser(mode)
            original = native_reference(seed,choose)
            env,prompts,metrics = run_adapter(seed,choose)
            exact = (original['agents']==env.agents and original['logs']==env.logs
                     and original['prompts']==prompts)
            if not exact:
                raise AssertionError((seed,mode))
            records.append(dict(seed=seed,scripted_action_tape=mode,
                                native_decisions=len(original['prompts']),sdk_decisions=len(prompts),
                                native_prompt_final_state_and_log_exact=True,
                                actual_source_years=metrics[-1]['actual_source_years']))
    hashes = {p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                         git_blob=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest())
              for p in UPSTREAM.iterdir() if p.is_file()}
    report = dict(status='complete_offline_mechanics_check',author_source_unchanged=before==hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  source_files=hashes,protocol_comparisons=len(records),records=records,
                  total_native_scripted_decisions=sum(x['native_decisions'] for x in records),
                  total_sdk_scripted_decisions=sum(x['sdk_decisions'] for x in records),
                  actual_api_requests=0,real_jev_decisions=0,
                  not_evidence_of='Gemma/Jev behavioral agreement, full paper replication, or human fidelity')
    out = Path('docs/llm_scope_review/wrr_mechanics_verification.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('records','source_files')},indent=2))


if __name__ == '__main__':
    main()
