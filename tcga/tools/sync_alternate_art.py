"""Refresh declared Arena variants from canonical cards; preserve the grouping name.

Add altImages entries in cards.json with image, label, release and arenaId.
Run after card/text updates so variants cannot retain stale effects or statistics.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://decclesia.github.io/SJTCGP/'

def synchronize(metadata, arena, root=ROOT):
    for card in metadata:
        for art in card.get('altImages', []):
            if not art.get('arenaId'):
                continue
            variant = copy.deepcopy(arena[card['number']])
            variant['id'] = art['arenaId']
            variant['Release'] = art.get('release', variant['Release'])
            variant['Artwork'] = art.get('label', 'Alt Art')
            digest = hashlib.sha256((root / art['image']).read_bytes()).hexdigest()[:12]
            url = BASE + art['image'] + '?v=' + digest
            variant['image'] = variant['face']['front']['image'] = url
            arena[variant['id']] = variant
    return arena

if __name__ == '__main__':
    metadata = json.loads((ROOT / 'cards.json').read_text(encoding='utf-8-sig'))
    path = ROOT / 'tcga/cards.json'
    arena = synchronize(metadata, json.loads(path.read_text(encoding='utf-8-sig')))
    path.write_text(json.dumps(arena, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
