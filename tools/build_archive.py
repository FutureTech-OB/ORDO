"""Export compact real pilot evidence; never copy credentials or session files."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('pilot_directory')
    args = p.parse_args()
    source = Path(args.pilot_directory)
    summary = json.loads((source/'results_summary.json').read_text(encoding='utf-8'))
    checkpoint = json.loads((source/'checkpoint.json').read_text(encoding='utf-8'))
    worlds = [dict(id=w['id'], seed=w['seed'], n=w['n'], policy=w['policy'], metrics=w['metrics'])
              for w in checkpoint['worlds']]
    archive = dict(kind='archived_jev', title='Management guidance × failed-experiment penalty',
                   date='2026-10-15', worlds=worlds, summary=summary,
                   provenance={name: hashlib.sha256((source/name).read_bytes()).hexdigest()
                               for name in ['results_summary.json', 'checkpoint.json', 'config.json']},
                   evidence_status='Completed pilot; three paired seeds, 12 rounds. No human validation.',
                   distinction='Department contact and adoption permission modules were added after this pilot; these results do not evaluate them.')
    destination = Path(__file__).resolve().parents[1]/'examples'/'archived_pilot.json'
    destination.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Exported {len(worlds)} worlds to {destination.name}')


if __name__ == '__main__':
    main()
