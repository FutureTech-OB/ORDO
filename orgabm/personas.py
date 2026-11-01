"""Portable Persona records and deterministic population construction.

Import is local and explicit: no dataset downloads, model calls or executable
templates. Source metadata is retained for audits, never passed as instructions.
"""
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import random
from .randomness import stable_seed

MAX_RECORDS = 20000
FIELDS = {'id', 'name', 'description', 'background', 'traits', 'skills', 'goals', 'source'}
SOURCES = {
    'custom': {},
    'nemotron': {'dataset': 'nvidia/Nemotron-Personas-USA', 'license': 'CC-BY-4.0',
                 'url': 'https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA'},
    'personahub': {'dataset': 'proj-persona/PersonaHub', 'license': 'CC-BY-NC-SA-4.0',
                  'url': 'https://huggingface.co/datasets/proj-persona/PersonaHub'},
    'finepersonas': {'dataset': 'argilla/FinePersonas-v0.1', 'license': 'llama3',
                    'url': 'https://huggingface.co/datasets/argilla/FinePersonas-v0.1'},
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _text(value, label, maximum=12000):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'{label} must be text of at most {maximum} characters.')
    return value


def _json_value(value, depth=0):
    if depth > 5:
        raise ValueError('Persona attributes are nested too deeply.')
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _json_value(item, depth+1)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json_value(item, depth+1)
        return
    raise ValueError('Persona attributes must be finite JSON values.')


def validate_persona(raw):
    if not isinstance(raw, dict) or set(raw)-FIELDS:
        raise ValueError('Unknown Persona fields; use a field map for external columns.')
    identifier = _text(raw.get('id'), 'Persona id', 200)
    if not identifier.strip():
        raise ValueError('Persona id cannot be empty.')
    record = dict(id=identifier, name=_text(raw.get('name', ''), 'name', 200),
                  description=_text(raw.get('description', ''), 'description'))
    for key in ['background', 'traits', 'skills', 'source']:
        value = raw.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f'{key} must be an object.')
        _json_value(value)
        record[key] = copy.deepcopy(value)
    goals = raw.get('goals', [])
    if not isinstance(goals, list) or any(not isinstance(x, str) for x in goals):
        raise ValueError('goals must be a list of strings.')
    record['goals'] = list(goals)
    if not any(record[k] for k in ['description', 'background', 'traits', 'skills', 'goals']):
        raise ValueError('A Persona needs at least one substantive attribute.')
    if len(json.dumps(record, ensure_ascii=False)) > 32000:
        raise ValueError('Persona record exceeds 32,000 characters.')
    return record


def import_personas(rows, *, preset='custom', field_map=None, source=None):
    """Normalize an iterable of records (including a Hugging Face dataset slice).

    field_map maps canonical destinations to dotted source columns, e.g.
    {"id":"person_id", "background.occupation":"job", "description":"bio"}.
    Built-in adapters retain the original dataset ID and optional revision metadata.
    """
    if preset not in SOURCES:
        raise ValueError('Unknown Persona preset.')
    if source is not None and not isinstance(source, dict):
        raise ValueError('source must be an object.')
    if field_map is not None:
        if not isinstance(field_map, dict) or not field_map:
            raise ValueError('field_map must be a nonempty object.')
        for target, column in field_map.items():
            if not isinstance(target, str) or not isinstance(column, str):
                raise ValueError('Field map paths must be strings.')
            parts = target.split('.')
            if not (len(parts) == 1 and target in FIELDS or
                    len(parts) == 2 and parts[0] in ['background', 'traits', 'skills', 'source'] and parts[1]):
                raise ValueError('Invalid canonical field map destination.')
        if any(t.split('.')[0] in field_map for t in field_map if '.' in t):
            raise ValueError('Overlapping field map destinations.')
    result, seen = [], set()
    for index, row in enumerate(rows):
        if index >= MAX_RECORDS:
            raise ValueError('Import at most 20,000 records at a time; select a dataset subset first.')
        if not isinstance(row, dict):
            raise ValueError('Each imported row must be an object.')
        if field_map:
            out = {}
            for target, column in field_map.items():
                value = row
                for part in column.split('.'):
                    if not isinstance(value, dict) or part not in value:
                        raise ValueError(f'Missing mapped column: {column}')
                    value = value[part]
                parts = target.split('.')
                if len(parts) == 2:
                    out.setdefault(parts[0], {})[parts[1]] = value
                else:
                    out[target] = value
        elif preset == 'nemotron':
            out = {'id': row.get('uuid', f'nemotron-{index}'),
                   'description': row.get('professional_persona') or row.get('persona', ''),
                   'background': {k: row[k] for k in ['age', 'sex', 'education_level', 'occupation',
                        'city', 'state', 'country', 'cultural_background'] if k in row},
                   'skills': {'description': row.get('skills_and_expertise', '')},
                   'traits': {'general_description': row.get('persona', '')},
                   'goals': [row['career_goals_and_ambitions']] if row.get('career_goals_and_ambitions') else []}
        elif preset in ['personahub', 'finepersonas']:
            out = {'id': row.get('id', f'{preset}-{index}'), 'description': row.get('persona', ''),
                   'background': {'labels': row['labels']} if 'labels' in row else {}}
        else:
            out = copy.deepcopy(row)
        out.setdefault('id', f'custom-{index}')
        if type(out['id']) is int:
            out['id'] = str(out['id'])
        if not isinstance(out.get('source', {}), dict):
            raise ValueError('source must be an object.')
        out['source'] = {**SOURCES[preset], **(source or {}), **out.get('source', {})}
        record = validate_persona(out)
        if record['id'] in seen:
            raise ValueError('Duplicate Persona IDs in the source pool.')
        seen.add(record['id'])
        result.append(record)
    if not result:
        raise ValueError('Persona import is empty.')
    return result


def _rows(stream, format):
    if format == 'jsonl':
        for line in stream:
            if line.strip():
                yield json.loads(line)
    elif format == 'csv':
        for row in csv.DictReader(stream):
            # Nested canonical attributes may be encoded as JSON in CSV cells.
            for key in ['background', 'traits', 'skills', 'goals', 'source']:
                if key in row and row[key]:
                    row[key] = json.loads(row[key])
                elif key in row:
                    del row[key]
            yield row
    elif format == 'json':
        data = json.load(stream)
        if not isinstance(data, list):
            raise ValueError('JSON Persona import must be an array of records.')
        yield from data
    else:
        raise ValueError('Import format must be json, jsonl or csv.')


def parse_personas(text, *, format='json', **kwargs):
    return import_personas(_rows(io.StringIO(text.lstrip('\ufeff')), format), **kwargs)


def load_personas(path, *, limit=MAX_RECORDS, **kwargs):
    """Load JSON/JSONL/CSV locally. Stream CSV/JSONL and read at most limit rows.

    Parquet/Hugging Face users can pass selected rows to import_personas instead.
    """
    from itertools import islice
    if type(limit) is not int or not 1 <= limit <= MAX_RECORDS:
        raise ValueError('limit must be between 1 and 20,000.')
    path = Path(path)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return import_personas(islice(_rows(stream, path.suffix.lower().lstrip('.')), limit), **kwargs)


def validate_population(raw, agents):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw)-{'records', 'sampling', 'seed', 'weights'}:
        raise ValueError('population accepts records, sampling, seed and weights.')
    records = raw.get('records')
    if not isinstance(records, list):
        raise ValueError('population.records must be a list.')
    records = import_personas(records)
    mode = raw.get('sampling', 'without_replacement')
    if mode not in ['without_replacement', 'with_replacement', 'ordered']:
        raise ValueError('Unknown population sampling mode.')
    if mode == 'without_replacement' and len(records) < agents:
        raise ValueError('Too few Personas; supply more or explicitly sample with_replacement.')
    if mode == 'ordered' and len(records) != agents:
        raise ValueError('Ordered population needs exactly one Persona per agent.')
    result = {'records': records, 'sampling': mode}
    if 'seed' in raw:
        if type(raw['seed']) is not int or not 0 <= raw['seed'] < 2**32:
            raise ValueError('Population seed must be a nonnegative 32-bit integer.')
        result['seed'] = raw['seed']
    if 'weights' in raw:
        weights = raw['weights']
        if mode != 'with_replacement' or not isinstance(weights, list) or len(weights) != len(records):
            raise ValueError('Weights require with_replacement and one weight per source record.')
        if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in weights) or not math.isfinite(sum(weights)) or sum(weights) <= 0:
            raise ValueError('Population weights must be finite, nonnegative and have positive total.')
        result['weights'] = list(weights)
    return result


def build_population(config):
    population = config.get('population')
    if population is None:
        return [None] * config['agents']
    records, n = population['records'], config['agents']
    rng = random.Random(stable_seed('persona_population', population.get('seed', config['seed'])))
    if population['sampling'] == 'ordered':
        indices = list(range(n))
    elif population['sampling'] == 'with_replacement':
        indices = rng.choices(range(len(records)), weights=population.get('weights'), k=n)
    else:
        indices = rng.sample(range(len(records)), n)
    # A new agent keeps independent state even when two source Persona IDs match.
    return [copy.deepcopy(records[i]) for i in indices]


def private_persona(record):
    return {k: copy.deepcopy(v) for k, v in record.items() if k not in ['id', 'source']}
