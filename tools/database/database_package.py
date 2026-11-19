"""Build a protected delta locally from committed files and a pinned prior manifest."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic

CATALOGUES = ("cards.json", "card-text.json", "accessories.json", "energy-markers.json")
# Approved Red TKG policy, SHA-256 83a89e78662ea27032b3311bce1aeef813b968ecdd4c881be92d8852aa97a227.
ST1_ACCESSORIES = frozenset("""
TKN-001 TOKEN-CSM TOKEN-ENERGY-GENERIC TOKEN-GKA TOKEN-GT-CSM TOKEN-GT-GKA
TOKEN-GT-HNI TOKEN-GT-JBA TOKEN-GT-NRT TOKEN-GT-SMK TOKEN-HNI TOKEN-JBA TOKEN-NRT
TOKEN-SJM-CSM1 TOKEN-SJM-CSM2 TOKEN-SJM-GKA1 TOKEN-SJM-HNI1 TOKEN-SJM-HNI2
TOKEN-SJM-JBA1 TOKEN-SJM-JBA2 TOKEN-SJM-JBA3 TOKEN-SJM-NRT1 TOKEN-SJM-NRT2
TOKEN-SJM-SMK1 TOKEN-SJM-SMK2 TOKEN-SJM-SMK3 TOKEN-SMK
""".split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def digest(data):
    return sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def art_path(name):
    p = PurePosixPath(name)
    require(p.parts and p.parts[0] in {"images", "tcga"} and len(p.parts) > 1
            and str(p) == name and ".." not in p.parts and not re.search(r'[\\:?#\x00]', name)
            and all(not PureWindowsPath(s).is_reserved() and not s.endswith((" ", ".")) for s in p.parts),
            f"Invalid art path: {name}")
    return name


def index(rows, key):
    mapped = {row[key]: row for row in rows}
    require(len(mapped) == len(rows), f"Duplicate {key} in input")
    return mapped


def pinned_json(path, expected_hash):
    data = path.read_bytes()
    require(digest(data) == expected_hash, f"Hash mismatch: {path}")
    return json.loads(data)


def build_policy(policy, cards, accessories, energy, additions=()):
    groups = index(policy["groups"], "id")
    require(policy["schemaVersion"] == 1 and policy["defaultEnabledGroups"] == ["ST1"], "Unexpected policy defaults")
    for group_id, accessory_id in additions:
        ids = groups[group_id]["accessoryIds"]
        require(accessory_id in accessories and accessory_id not in ids, f"Invalid addition: {accessory_id}")
        ids.append(accessory_id)
        ids.sort()
    ids = groups["ST1"]["accessoryIds"]
    require(len(ids) == 27 and set(ids) == ST1_ACCESSORIES, "ST1 must contain exactly the approved 27 accessories")
    assigned = Counter()
    for group in groups.values():
        paths = set()
        for key, catalogue in (("cardIds", cards), ("accessoryIds", accessories), ("energyMarkerIds", energy)):
            members = group[key]
            require(len(set(members)) == len(members), f"Duplicate {key} in {group['id']}")
            for item in members:
                record = catalogue[item]
                paths.add(art_path(record["image"]))
                if key == "cardIds":
                    assigned[item] += 1
                    paths.update(art_path(a["image"]) for a in record.get("altImages", []))
        group["artPaths"] = sorted(paths)
    require(assigned == Counter(cards.keys()), "Every canonical card needs exactly one approved group")
    return policy


def install_output(staged, destination):
    # A complete directory becomes visible in one rename. A retry must match it exactly.
    if not destination.exists():
        staged.rename(destination)
        return
    def paths(folder):
        return {p.relative_to(folder) for p in folder.rglob("*") if p.is_file()}
    names = paths(staged)
    require(names == paths(destination), f"Existing output has different files: {destination}")
    for name in names:
        require((staged / name).read_bytes() == (destination / name).read_bytes(), f"Existing output differs: {name}")


def pack_delta(repo, commit, baseline_file, baseline_sha, policy_file, destination, additions=(), removals=(),
               canonical_base=None):
    require(re.fullmatch("[0-9a-f]{40}", commit), "Expected a full canonical commit")
    baseline = pinned_json(baseline_file, baseline_sha)
    base = baseline["sourceCommit"]
    require(re.fullmatch("[0-9a-f]{40}", base), "Invalid baseline commit")
    canonical_base = canonical_base or git(repo, "rev-parse", commit + "^").decode().strip()
    require(re.fullmatch("[0-9a-f]{40}", canonical_base), "Invalid canonical base")
    git(repo, "merge-base", "--is-ancestor", base, canonical_base)
    git(repo, "merge-base", "--is-ancestor", canonical_base, commit)
    prior = index(baseline["files"], "path")
    if base != canonical_base:
        intervening = git(repo, "diff", "--no-renames", "--name-only", "-z", base, canonical_base)
        touched = set(intervening.decode().split("\0")) & prior.keys()
        require(not touched, f"Protected baseline predates canonical changes: {sorted(touched)}")
    policy = pinned_json(policy_file, prior["policy.json"]["sha256"])
    data = {p: git(repo, "show", f"{commit}:{p}") for p in CATALOGUES}
    cards = index(json.loads(data["cards.json"]), "number")
    accessories = index(json.loads(data["accessories.json"]), "id")
    if digest(data["accessories.json"]) != prior["accessories.json"]["sha256"]:
        old_accessories = index(json.loads(git(repo, "show", f"{base}:accessories.json")), "id")
        new_ids = accessories.keys() - old_accessories.keys()
        require(new_ids <= {item for _, item in additions}, f"Missing explicit allocation for {sorted(new_ids)}")
    energy = index(json.loads(data["energy-markers.json"]), "id")
    require(set(cards) == set(json.loads(data["card-text.json"])), "Card/text IDs differ")
    policy = build_policy(policy, cards, accessories, energy, additions)
    data["policy.json"] = encode(policy)
    art = {art_path(x["image"]) for rows in (cards, accessories, energy) for x in rows.values()}
    art.update(art_path(a["image"]) for c in cards.values() for a in c.get("altImages", []))
    desired = art | set(data)
    removed = sorted(prior.keys() - desired)
    require(removed == sorted(removals), f"Unexpected removals: {removed}")
    blobs = {}
    for entry in git(repo, "ls-tree", "-rz", commit).split(b"\0"):
        if entry:
            meta, name = entry.split(b"\t", 1)
            mode, kind, blob = meta.split()
            if kind == b"blob" and mode in (b"100644", b"100755"):
                blobs[name.decode()] = blob.decode()
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows, changed = [], []
    with TemporaryDirectory(dir=destination.parent) as tmp:
        out = Path(tmp) / "output"
        stage = out / "protected-delta"
        stage.mkdir(parents=True)
        for path in sorted(desired):
            old = prior.get(path)
            if path == "policy.json":
                unchanged = old["sha256"] == digest(data[path])
            else:
                unchanged = old and old.get("gitBlob") == blobs[path]
            if unchanged:
                rows.append(old)
                continue
            body = data[path] if path in data else git(repo, "cat-file", "blob", blobs[path])
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            require(target.read_bytes() == body, f"Readback failed: {path}")
            kind = "generated-policy" if path == "policy.json" else "catalogue-json" if path in data else "referenced-art"
            row = dict(path=path, kind=kind, sha256=digest(body), bytes=len(body))
            if path != "policy.json":
                row["gitBlob"] = blobs[path]
            rows.append(row)
            changed.append(path)
        manifest = dict(schemaVersion=1, sourceCommit=commit, baseCommit=canonical_base,
                        stage=str(destination / "protected-delta"), stageKind="delta-only",
                        baselineManifestSha256=baseline_sha, changedFiles=changed, files=rows)
        if removed:
            manifest["removedFiles"] = removed
        if canonical_base != base:
            manifest["protectedBaseCommit"] = base
        (out / "source_file_manifest.json").write_bytes(encode(manifest))
        install_output(out, destination)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "baseline", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--base-commit", help="Canonical prior commit for a multi-commit batch (default: parent)")
    parser.add_argument("--baseline-sha256", required=True)
    parser.add_argument("--add-accessory", nargs=2, action="append", default=[], metavar=("GROUP", "ID"))
    parser.add_argument("--remove-path", action="append", default=[])
    args = parser.parse_args()
    started = monotonic()
    result = pack_delta(args.repo, args.commit, args.baseline, args.baseline_sha256,
                        args.policy, args.output, args.add_accessory, args.remove_path, args.base_commit)
    print(json.dumps({"phase": "protected-package", "sourceCommit": result["sourceCommit"],
                      "changed": result["changedFiles"], "total": len(result["files"]),
                      "elapsedSeconds": round(monotonic() - started, 3)}))
