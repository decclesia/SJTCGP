"""Build only the isolated, Worker-protected database-source catalogue and policy.

Uses current planner cycle ownership and exact committed database bytes. It never
modifies the canonical database, planner, simulator, or public UI source.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

from database_package import art_path, build_policy, digest, git, pinned_json, require


SOURCE_JSON = ('cards.json', 'card-text.json', 'accessories.json', 'energy-markers.json')


def load_planner(file: Path) -> tuple[dict, str]:
    original = file.read_bytes()
    code = "const fs=require('fs'),vm=require('vm');const c={window:{}};vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),c);process.stdout.write(JSON.stringify(c.window.SJTCGP_SEED));"
    planner = json.loads(subprocess.check_output(['node', '-e', code, str(file)]))
    return planner, digest(original)


def write_json(file: Path, value: object) -> bytes:
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(data)
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path.cwd())
    ap.add_argument('--planner', type=Path, required=True)
    ap.add_argument('--output', type=Path, help='Local directory for a complete stage, report and manifest')
    ap.add_argument('--stage', type=Path)
    ap.add_argument('--commit', help='Exact source commit (default: local HEAD)')
    ap.add_argument('--groups', default='auto', help='Expected approved group order, or auto to use the pinned policy')
    ap.add_argument('--expected-cards', type=int, default=1401)
    ap.add_argument('--expected-alternates', type=int, default=272)
    ap.add_argument('--expected-accessories', type=int, default=188)
    ap.add_argument('--expected-receipts', type=int, default=215)
    ap.add_argument('--expected-planner-version', type=int, default=176)
    ap.add_argument('--expected-art-files', type=int, default=1861)
    ap.add_argument('--incremental', action='store_true', help='Reuse prior manifest proofs for source blobs unchanged at the new commit')
    ap.add_argument('--report', type=Path)
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--approved-policy', type=Path, required=True, help='Reviewed group memberships for this source')
    ap.add_argument('--policy-sha256', required=True, help='Trusted SHA-256 of the approved policy bytes')
    args = ap.parse_args()
    if not __debug__:
        ap.error("Run with Python assertions enabled")
    args.commit = args.commit or git(args.repo, 'rev-parse', 'HEAD').decode().strip()
    if args.output:
        if any((args.stage, args.report, args.manifest)):
            ap.error('Use --output or the separate stage/report/manifest paths')
        args.stage = args.output / 'database-source'
        args.report = args.output / 'package_report.json'
        args.manifest = args.output / 'source_file_manifest.json'
    if not all((args.stage, args.report, args.manifest)):
        ap.error('Specify --output or all three stage/report/manifest paths')
    started = time.monotonic()
    repo, stage = args.repo.resolve(), args.stage.resolve()
    assert repo != stage and repo not in stage.parents and stage not in repo.parents, 'Stage must be isolated from canonical database'
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    require(git(repo, 'rev-parse', '--verify', args.commit + '^{commit}').decode().strip() == args.commit,
            'Supply a full canonical commit ID')
    prior_manifest = json.loads(args.manifest.read_text(encoding='utf-8')) if args.incremental else None
    prior_report = json.loads(args.report.read_text(encoding='utf-8')) if args.incremental else None
    if prior_manifest:
        assert Path(prior_manifest['stage']).resolve() == stage
        assert prior_report['status'] == 'complete-staged-not-deployed'
        assert prior_report['sourceCommit'] == prior_manifest['sourceCommit']
    prior_rows = {r['path']: r for r in prior_manifest['files']} if prior_manifest else {}
    planner, planner_sha = load_planner(args.planner)
    assert planner['version'] == args.expected_planner_version, planner['version']
    receipt_state = planner['alternateArtworkInventory']
    assert receipt_state['receivedArtworks'] == args.expected_receipts
    assert sum(len(r['entries']) for r in receipt_state['releases']) == args.expected_receipts
    receipt_sha = digest(json.dumps(receipt_state, ensure_ascii=False, sort_keys=True).encode())

    # Read exact committed JSON, avoiding working-tree CRLF conversions.
    source_bytes = {name: git(repo, 'show', f'{args.commit}:{name}') for name in SOURCE_JSON}
    cards = json.loads(source_bytes['cards.json'])
    text = json.loads(source_bytes['card-text.json'])
    accessories = json.loads(source_bytes['accessories.json'])
    energy = json.loads(source_bytes['energy-markers.json'])
    cards_by_id = {c['number']: c for c in cards}
    accessories_by_id = {a['id']: a for a in accessories}
    energy_by_id = {e['id']: e for e in energy}
    assert len(cards) == len(cards_by_id) == args.expected_cards
    assert set(text) == set(cards_by_id)
    assert len(accessories_by_id) == len(accessories) == args.expected_accessories
    alternate_count = sum(len(c.get('altImages', [])) for c in cards)
    assert alternate_count == args.expected_alternates

    policy = pinned_json(args.approved_policy, args.policy_sha256)
    policy = build_policy(policy, cards_by_id, accessories_by_id, energy_by_id)
    groups = policy['groups']
    require(args.groups == 'auto' or args.groups.split(',') == [g['id'] for g in groups],
            'Requested groups differ from the approved allocation')
    derivation = [dict(id=g['id'], cardCount=len(g['cardIds']), accessoryCount=len(g['accessoryIds']),
                       energyMarkerCount=len(g['energyMarkerIds']), artPathCount=len(g['artPaths']),
                       allocationSourceSha256=args.policy_sha256) for g in groups]
    # Pinned sorted ST1 card identities from the approved inventory.
    st1_ids = groups[0]['cardIds']
    require(groups[0]['id'] == 'ST1' and digest('\n'.join(st1_ids).encode()) == '25e0ee517eef93a319383195246ea9555d22853be735a15506cb7da1f56bbf48',
            'ST1 card identities differ from the approved inventory')
    assert len(groups[0]['cardIds']) == 210 and 'PUP-041' in groups[0]['cardIds']
    assert len([a for i in groups[0]['cardIds'] for a in cards_by_id[i].get('altImages', [])]) == 40

    all_art = {art_path(c['image']) for c in cards}
    all_art.update(art_path(a['image']) for c in cards for a in c.get('altImages', []))
    all_art.update(art_path(a['image']) for a in accessories)
    all_art.update(art_path(e['image']) for e in energy)
    assert len(all_art) == args.expected_art_files, len(all_art)
    tree = {}
    for row in git(repo, 'ls-tree', '-rz', args.commit).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, git_sha = meta.decode().split()
        if kind == 'blob':
            tree[name.decode()] = git_sha
    assert all(p in tree for p in all_art), sorted(all_art - tree.keys())
    stage.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for name, data in source_bytes.items():
        target = stage / name
        old_row = prior_rows.get(name)
        if old_row and old_row.get('gitBlob') == tree[name]:
            assert target.is_file() and target.stat().st_size == old_row['bytes'], name
            assert digest(data) == old_row['sha256'], name
            manifest_rows.append(dict(old_row))
            continue
        target.write_bytes(data)
        assert digest(target.read_bytes()) == digest(data), name
        manifest_rows.append({'path': name, 'kind': 'catalogue-json', 'bytes': len(data), 'sha256': digest(data), 'gitBlob': tree[name]})
    policy_bytes = (json.dumps(policy, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if prior_rows.get('policy.json', {}).get('sha256') == digest(policy_bytes):
        target = stage / 'policy.json'
        assert target.is_file() and target.stat().st_size == prior_rows['policy.json']['bytes']
    else:
        (stage / 'policy.json').write_bytes(policy_bytes)
    require((stage / 'policy.json').read_bytes() == policy_bytes, 'Policy readback failed')
    manifest_rows.append({'path': 'policy.json', 'kind': 'generated-policy', 'bytes': len(policy_bytes), 'sha256': digest(policy_bytes)})

    def copy_art(rel: str) -> dict:
        old_row = prior_rows.get(rel)
        if old_row and old_row.get('gitBlob') == tree[rel]:
            target = stage / rel
            assert target.is_file() and target.stat().st_size == old_row['bytes'], rel
            return dict(old_row)
        local = repo / rel
        data = local.read_bytes() if local.is_file() else b''
        blob_sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob_sha != tree[rel]:
            data = git(repo, 'show', f'{args.commit}:{rel}')
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == tree[rel], rel
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        assert stage in target.resolve().parents, rel
        target.write_bytes(data)
        expected = digest(data)
        assert digest(target.read_bytes()) == expected, rel
        return {'path': rel, 'kind': 'referenced-art', 'bytes': len(data), 'sha256': expected, 'gitBlob': tree[rel]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        manifest_rows.extend(pool.map(copy_art, sorted(all_art)))
    manifest_rows.sort(key=lambda r: r['path'])
    staged_files = sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    assert staged_files == sorted(row['path'] for row in manifest_rows), 'Stage contains unreferenced or missing files'
    assert not any(p.endswith('.js') for p in staged_files), 'Full JS payload must not be staged'
    assert digest(args.planner.read_bytes()) == planner_sha, 'Planner changed while packaging'
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == head, 'Checkout changed while packaging')
    manifest = {'schemaVersion': 1, 'sourceCommit': args.commit, 'stage': str(stage), 'files': manifest_rows}
    if prior_manifest:
        backup = args.manifest.with_name(args.manifest.stem + '.before-' + args.commit[:7] + args.manifest.suffix)
        if not backup.exists():
            write_json(backup, prior_manifest)
    write_json(args.manifest, manifest)
    report = {'status': 'complete-staged-not-deployed', 'sourceCommit': args.commit, 'plannerVersion': planner['version'], 'stage': str(stage), 'policyPath': str(stage / 'policy.json'), 'manifest': str(args.manifest.resolve()), 'defaultEnabledGroups': ['ST1'], 'groups': derivation, 'counts': {'canonicalCards': len(cards), 'alternateImages': alternate_count, 'accessories': len(accessories), 'energyMarkers': len(energy), 'referencedArtFiles': len(all_art), 'catalogueJsonFiles': 4, 'generatedPolicyFiles': 1, 'stagedFiles': len(staged_files), 'totalBytes': sum(r['bytes'] for r in manifest_rows)}, 'policySha256': digest(policy_bytes), 'preservation': {f'all{len(cards)}IDsAssignedExactlyOnce': True, 'ST1Exact210IDsWithPUP041': True, 'allIdentityAAsIncludedRegardlessRelease': True, 'plannerSourceUnchangedSha256': planner_sha, 'releaseAAReceiptsUnchanged': receipt_state['receivedArtworks'], 'releaseAAReceiptStateSha256': receipt_sha, 'noRepositorySimulatorOrPlannerWrites': True, 'artBytesMatchCommittedBlobs': True, 'noJSPayloadFilesStaged': True}, 'sourceJsonHashes': {name: digest(data) for name, data in source_bytes.items()}, 'elapsedSeconds': round(time.monotonic() - started, 3)}
    if prior_manifest:
        changed = sorted(r['path'] for r in manifest_rows if r['path'] not in prior_rows or r['sha256'] != prior_rows[r['path']]['sha256'])
        report['incremental'] = {'previousSourceCommit': prior_manifest['sourceCommit'], 'verifiedChangedFiles': changed, 'verifiedChangedFileCount': len(changed), 'unchangedFilesEvidenceReused': len(manifest_rows) - len(changed), 'policyUnchanged': prior_report['policySha256'] == digest(policy_bytes), 'proof': 'Unchanged committed Git blobs retain prior SHA256/copy-readback evidence; changed files alone copied and readback-verified.'}
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
