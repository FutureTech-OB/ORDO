"""Offline complete-candidate/API-scale audit. No credential access or API call."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def full_exploration_candidates(position=45150,visited=frozenset({45150})):
    """Every author cutoff offset, including the original wrapped duplicates."""
    x,y=position%300,position//300
    for dx in range(-150,151):
        for dy in range(-150,151):
            if dx==dy==0:continue
            distance=int(math.hypot(dx,dy))
            if distance>150:continue
            target=(x+dx)%300+300*((y+dy)%300)
            if target in visited:continue
            yield dict(offset=[dx,dy],target=target,distance=distance)


def audit():
    candidates=list(full_exploration_candidates());criteria={f'offset-{i}':dict(destination=c['target'],
        x=c['target']%300,y=c['target']//300,travel_distance=c['distance'],population=0,previous_visits=0)
        for i,c in enumerate(candidates)}
    payload=dict(state='First-period focal resident at center45150. Choose its next previously unvisited destination.',
        questions={'resident-0':dict(type='choice',instructions='Predict the destination choice from the complete author candidate space.',criteria=criteria)})
    raw=json.dumps(payload,separators=(',',':')).encode()
    n=30000;paper_steps=20000;code_steps=20001;repeats=5
    return dict(status='full_direct_choice_blocked_not_running_jev',source_doi='10.1038/s43588-021-00160-6',
        initial_exploration_offset_options=len(candidates),initial_unique_wrapped_destinations=len({c['target'] for c in candidates}),
        json_body_bytes_one_full_candidate_question=len(raw),body_sha256=hashlib.sha256(raw).hexdigest(),
        tokenizer_note='No Jev tokenizer or provider measurement for this unsupported full candidate payload; bytes are not tokens.',
        documented_typesafe_choice_option_limit=255,openrouter_same_limit='Not separately established for this endpoint;no claim of support beyond255.',
        code_entrypoint_updates=n*code_steps*repeats,paper_profile_updates=n*paper_steps*repeats,
        per_run_paper_period_barriers=paper_steps,within_period='Independent given frozen population and individual history;fresh decisions can be batched.',
        cross_period='Must commit all30000 movement outcomes before computing next-period population.',
        price_checked_20261030=dict(input_usd_per_million=.042,output_usd_per_million=0,
            source='https://openrouter.ai/typesafe/jev-1.14'),
        hypothetical_paper_costs=[dict(assumed_input_tokens_per_judgment=t,total_input_tokens=t*n*paper_steps*repeats,
            estimated_input_cost_usd=t*n*paper_steps*repeats*.042/1000000) for t in (100,1000,10000)],
        hypothetical_batch64_requests_per_paper_suite=math.ceil(n/64)*paper_steps*repeats,
        call_count_note='Assumes one supported complete-choice question per agent update,currently unavailable.Three-level hierarchical choice changes interface and raises up to9billion judgments;not approved or run.',
        no_paid_calls=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path)
    a=p.parse_args();report=audit();text=json.dumps(report,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text,encoding='utf-8')
    print(text)
