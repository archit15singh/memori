"""Read-only recall from an explicit complete snapshot, using the existing engine."""
import hashlib
import json
import math
from pathlib import Path
import re

from lorevell import PyLorevell
from .local_state import locked, read_json, write_json


def validated(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('version') != 1 or snapshot.get('complete') is not True:
        raise ValueError('Expected a complete version 1 source snapshot')
    source = snapshot.get('source_id')
    if not isinstance(source, str) or not source.strip() or len(source) > 200:
        raise ValueError('Snapshot needs a source_id')
    if snapshot.get('sync_status') not in ('current', 'partial', 'offline'):
        raise ValueError('Snapshot needs current, partial or offline sync_status')
    records = snapshot.get('records')
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError('Snapshot records must be a list of at most 10000 entries')
    ids, result = set(), []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Each record must be an object')
        ident = record.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', ident) or ident in ids:
            raise ValueError('Record IDs must be unique safe strings')
        ids.add(ident)
        for key in ('title', 'content', 'source_url', 'source_revision'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f'Record needs nonempty {key}')
        timestamp = record.get('updated_at')
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or timestamp < 0:
            raise ValueError('updated_at must be a finite nonnegative source timestamp')
        result.append({key: record[key] for key in ('id', 'title', 'content', 'source_url', 'source_revision')} |
                      {'updated_at': timestamp, 'source_path': str(record.get('source_path', '')),
                       'immutable_source': True})
    return source, sorted(result, key=lambda r: r['id'])


def recall(snapshot, cache_dir, query='', limit=3, text_only=False, index_only=False):
    source, records = validated(snapshot)  # Validate everything before any cache mutation.
    if not index_only and (not query.strip() or len(query) > 1000):
        raise ValueError('Supply a query up to 1000 characters, or use --index-only')
    if limit < 0 or limit > 100:
        raise ValueError('Recall limit must be between 0 and 100')
    root = Path(cache_dir).expanduser()
    if root.is_symlink():
        raise ValueError('Recall cache must not be a symlink')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = root / 'source.json'
    owner = read_json(marker, None)
    if owner is not None:
        if not isinstance(owner, dict) or owner.get('version') != 1 or owner.get('source_id') != source:
            raise ValueError('This recall cache belongs to another source or has invalid ownership')
    elif any(p.name != 'recall.lock' for p in root.iterdir()):
        raise ValueError('Choose an empty dedicated recall cache, not an existing vault')
    root.chmod(0o700)
    fingerprint = hashlib.sha256(json.dumps([source, records], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with locked(root / 'recall.lock'):
        state = read_json(marker, {})
        if state and (state.get('version') != 1 or state.get('source_id') != source):
            raise ValueError('This recall cache belongs to another source')
        paths = [root / name for name in ('recall.sqlite', 'recall.sqlite-wal', 'recall.sqlite-shm')]
        if any(p.is_symlink() for p in paths):
            raise ValueError('Recall database must not be a symlink')
        changed = state.get('fingerprint') != fingerprint or not paths[0].exists()
        if changed:
            write_json(marker, {'version': 1, 'source_id': source, 'fingerprint': None})
            # Disposable projection only. Removing the old index first prevents
            # removed/withheld records surviving a failed rebuild. No archives.
            for path in paths:
                path.unlink(missing_ok=True)
        db = PyLorevell(str(paths[0]))
        try:
            if changed:
                for record in records:
                    metadata = {k: v for k, v in record.items() if k not in ('content', 'id', 'updated_at')}
                    metadata['source_id'] = source
                    db.insert_with_id(record['id'], '# ' + record['title'] + '\n\n' + record['content'],
                                      metadata=metadata, created_at=record['updated_at'], updated_at=record['updated_at'])
                write_json(marker, {'version': 1, 'source_id': source, 'fingerprint': fingerprint})
            if not index_only and not text_only and limit:
                db.backfill_embeddings(batch_size=8)
            matches = [] if index_only else db.search(text=query, text_only=text_only, limit=limit)
            result = []
            for hit in matches:
                metadata = hit['metadata']
                result.append(dict(id=hit['id'], title=metadata['title'], content=hit['content'],
                                   source_url=metadata['source_url'], source_revision=metadata['source_revision'],
                                   source_path=metadata['source_path'], immutable_source=True, score=hit['score']))
            return {'source_id': source, 'sync_status': snapshot['sync_status'],
                    'synced_at': snapshot.get('synced_at'), 'indexed': len(records), 'rebuilt': changed,
                    'matches': result, 'notice': 'Local source snapshot; sync freshness is not semantic verification.'}
        finally:
            del db
