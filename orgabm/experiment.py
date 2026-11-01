import hashlib
import json
from pathlib import Path
import time
from . import __version__, kernel
from .organization import (validate_config, memberships, contact_sets, effective_policy,
                           observation, question, shared_state, rule_probabilities, apply_round)
from .randomness import sample, stable_seed
from .workforce import build_workforce, workforce_metadata

SOURCE = dict(paper='Barkoczi & Galesic (2016), Nature Communications 7:13109',
              doi='10.1038/ncomms13109', repository='https://github.com/dnlbrkc/social_learning',
              commit='93b5f6fb18290ff67a5a676c9ef98a5aa3165f71',
              adaptation='Python reimplementation of NK social learning, with organization extensions; not an exact reproduction.')


def run(raw_config, engine=None, output=None):
    config = validate_config(raw_config)
    if config['engine'] == 'jev' and engine is None:
        raise ValueError('A live decision engine is required.')
    started = time.perf_counter()
    scores = kernel.landscape(config['seed'])
    policy = dict(id='organization', **effective_policy(config, 1))
    world = kernel.initialize(config['agents'], config['seed'], policy, config['engine'])
    labels = memberships(config)
    world['workforce'] = build_workforce(config, labels)
    initial_positions = list(world['positions'])
    traces, snapshots = [], []
    for t in range(1, config['rounds']+1):
        peers = contact_sets(config, labels, t)
        records = [observation(world, scores, config, labels, peers, a, t) for a in range(world['n'])]
        questions = {f't{t}_a{a}': question(r, config['seed'], t, a) for a, r in enumerate(records)}
        if engine is None:
            probabilities = [rule_probabilities(r, config['engine']) for r in records]
        else:
            answers = engine.decide(shared_state(config['rounds']), questions)
            if set(answers) != set(questions):
                raise ValueError('Missing or unexpected decisions; round was not advanced.')
            probabilities = [answers[f't{t}_a{a}'] for a in range(world['n'])]
        actions = [sample(p, stable_seed('action', config['seed'], t, a)) for a, p in enumerate(probabilities)]
        before = list(world['positions'])
        metric = apply_round(world, scores, config, labels, peers, actions, probabilities, t)
        for a in range(min(4, world['n'])):
            traces.append(dict(round=t, agent=a, observation=records[a], probabilities=probabilities[a],
                               requested_action=actions[a], feedback=world['histories'][a][-1]))
        displayed = min(80, world['n'])
        snapshots.append(dict(round=t, nodes=[dict(id=a, department=labels[a],
                              performance=float(scores[world['positions'][a]]), action=actions[a])
                              for a in range(displayed)],
                              edges=[[a,b] for a in range(displayed) for b in peers[a] if b < displayed]))
        if output:
            with (Path(output) / 'trajectory.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(dict(round=t, positions_before=before, actions=actions,
                    probabilities=probabilities, peers=peers, positions_after=world['positions'], metrics=metric))+'\n')
    elapsed = time.perf_counter()-started
    result = dict(schema_version='0.1', prototype_version=__version__, status='complete',
                  kind='fresh_jev' if engine else 'fresh_rule', config=config, source=SOURCE,
                  metrics=world['metrics'], traces=traces, snapshots=snapshots,
                  initial_state_sha256=hashlib.sha256(json.dumps(initial_positions).encode()).hexdigest(),
                  landscape_sha256=hashlib.sha256(scores.tobytes()).hexdigest(),
                  final_positions=world['positions'], final_balances=world['balances'],
                  departments=labels, elapsed_s=elapsed,
                  **workforce_metadata(config, world['workforce']),
                  decisions=config['agents']*config['rounds'], probability_reuse=False,
                  usage=engine.usage() if engine else dict(recorded_input_cost_usd=0, successful_requests=0),
                  caveats=['Simulation output; no human validation.',
                           'Rule engines ignore Persona, role descriptions, advisory text and identity labels; role action restrictions are enforced.',
                           'Permission threshold is an enforced rule, not a manager decision model.',
                           'Fresh organization runs differ from the archived pilot configuration.'])
    if output:
        root = Path(output)
        result['source_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in Path(__file__).parent.glob('*.py')}
        (root/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
