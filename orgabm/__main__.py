import argparse
import json
import math
from pathlib import Path
from .experiment import run
from .organization import validate_config


def main():
    parser = argparse.ArgumentParser(description='ORDO: Organizational Decision Modeling research prototype')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo')
    demo.add_argument('--port', type=int, default=8765)
    execute = commands.add_parser('run')
    execute.add_argument('--config', required=True)
    execute.add_argument('--output', required=True)
    execute.add_argument('--engine', choices=['best', 'conformity', 'jev'])
    execute.add_argument('--max-cost-usd', type=float, default=0.10)
    importer = commands.add_parser('import-personas', help='Normalize a local Persona dataset subset')
    importer.add_argument('--input', required=True)
    importer.add_argument('--output', required=True)
    importer.add_argument('--preset', choices=['custom', 'nemotron', 'personahub', 'finepersonas'], default='custom')
    importer.add_argument('--field-map', help='JSON file mapping canonical fields to source columns')
    importer.add_argument('--limit', type=int, default=20000)
    placement = commands.add_parser('assign-personas', help='Construct a population using Jev position-occupancy probabilities')
    placement.add_argument('--job', required=True, help='Assignment JSON with config, mode and optional threshold')
    placement.add_argument('--preview', action='store_true', help='Validate and count only; no API calls')
    placement.add_argument('--output', help='New directory for evidence and completed configuration')
    placement.add_argument('--max-cost-usd', type=float, default=0.10)
    placement.add_argument('--max-requests', type=int, default=0, help='Explicit upper allowance for native Jev requests')
    experiment = commands.add_parser('experiment', help='Preview or run a registered multi-world experiment plan')
    experiment.add_argument('--plan', required=True)
    experiment.add_argument('--preview', action='store_true')
    experiment.add_argument('--output', help='New experiment service directory')
    experiment.add_argument('--max-requests', type=int, default=0)
    experiment.add_argument('--max-cost-usd', type=float, default=0.10)
    args = parser.parse_args()
    if args.command == 'demo':
        from .server import serve
        serve(args.port)
        return
    if args.command == 'experiment':
        from .plans import expand_plan
        from .mcp_server import ExperimentService
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8-sig'))
        preview = expand_plan(plan)
        if args.preview:
            print(json.dumps({k:v for k,v in preview.items() if k!='configs'},ensure_ascii=False,indent=2))
            return
        if not args.output or Path(args.output).exists():
            parser.error('Provide a new --output directory.')
        if args.max_requests < preview['provider_requests']:
            parser.error('Set --max-requests to at least the preview upper bound.')
        service = ExperimentService(args.output,allow_paid=preview['provider_requests']>0,
            max_requests=args.max_requests,max_cost_usd=args.max_cost_usd)
        try:
            job = service.start(plan)
            service.jobs[job['id']].result()
            status = service.get(job['id'])
            print(json.dumps(dict(id=job['id'],status=status['status'],completed_worlds=status['completed_worlds'],
                path=str(service.root/job['id']),results=[dict(world=r['world'],final=r['final'],usage=r['usage']) for r in status['results']]),ensure_ascii=False,indent=2))
            if status['status']!='complete': raise SystemExit(1)
        finally:
            service.pool.shutdown()
        return
    if args.command == 'assign-personas':
        from .placement import preview_assignment, assign_personas, save_assignment
        job = json.loads(Path(args.job).read_text(encoding='utf-8-sig'))
        preview = preview_assignment(job)
        if args.preview:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return
        if not args.output:
            parser.error('Assignment execution requires --output.')
        if args.max_requests < preview['max_provider_requests']:
            parser.error('Set --max-requests to at least the preview maximum; no requests submitted.')
        if not math.isfinite(args.max_cost_usd) or args.max_cost_usd <= 0:
            parser.error('Budget must be a finite positive number.')
        output = Path(args.output)
        if output.exists():
            parser.error('Use a new assignment output directory.')
        from .engines import JevEngine
        engine = JevEngine(output, args.max_cost_usd, preview['batch_size'], concurrency=1)
        output.mkdir(parents=True)
        (output/'job.json').write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
        result = assign_personas(job, engine, output=output)
        save_assignment(result, output)
        print(json.dumps({k: result[k] for k in ['status','assigned','evaluated_pairs','missing_by_role','usage']}, ensure_ascii=False, indent=2))
        return
    if args.command == 'import-personas':
        from .personas import load_personas
        mapping = json.loads(Path(args.field_map).read_text(encoding='utf-8-sig')) if args.field_map else None
        records = load_personas(args.input, preset=args.preset, field_map=mapping, limit=args.limit)
        output = Path(args.output)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(records, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'records': len(records), 'output': str(output)}, ensure_ascii=False))
        return
    config = json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    if args.engine:
        config['engine'] = args.engine
    config = validate_config(config)
    if not math.isfinite(args.max_cost_usd) or args.max_cost_usd <= 0:
        parser.error('Budget must be a finite positive number.')
    output = Path(args.output)
    if output.exists():
        parser.error('Use a new output directory; existing results are never overwritten.')
    output.mkdir(parents=True)
    (output/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    engine = None
    if config['engine'] == 'jev':
        from .engines import JevEngine
        engine = JevEngine(output, args.max_cost_usd, config['batch_size'], config['concurrency'])
    result = run(config, engine, output)
    print(json.dumps(dict(status=result['status'], decisions=result['decisions'],
                         seconds=result['elapsed_s'], usage=result['usage']), indent=2))


if __name__ == '__main__':
    main()
