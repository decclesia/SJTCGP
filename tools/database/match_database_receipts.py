"""Match a database batch to the publisher's recorded live check. Read-only, offline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


def require(ok, message):
    if not ok:
        raise ValueError(message)


def match(source_path, prepared_path, publication_path, live_path):
    source = json.loads(source_path.read_bytes())
    publication_bytes = publication_path.read_bytes()
    publication = json.loads(publication_bytes)
    manifest_bytes = prepared_path.read_bytes()
    live_bytes = live_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    live = json.loads(live_bytes)

    commit = source["sourceCommit"]
    require(re.fullmatch("[0-9a-f]{40}", commit), "Invalid canonical source commit")
    for record in (manifest, publication, live):
        require(record["sourceCommit"] == commit, "Source commit mismatch")
    require(publication["status"] == live["status"] == "VERIFIED_LIVE", "Publication is pending")
    require(live["passed"] is True and publication.get("passed", True) is True, "Failed publication check")
    worker = publication["worker"]
    require(isinstance(worker, str) and worker and worker == live["worker"], "Worker mismatch")
    for name, value in publication.get("checks", {}).items():
        if name == "artAllowDenyPairs":
            require(type(value) is int and value > 0, "Invalid artwork access check count")
        else:
            require(value is True, f"Failed batch check: {name}")

    # The two publisher formats identify the same frozen live check in different ways.
    if "verification" in publication:
        live_ref = publication["verification"]["live"]
    else:
        refs = [r for r in publication["evidence"] if Path(r["path"]).name == "live.json"]
        require(len(refs) == 1, "Expected one live evidence file")
        live_ref = refs[0]
    require(sha256(live_bytes).hexdigest() == live_ref["sha256"], "Live evidence hash mismatch")
    manifest_hash = sha256(manifest_bytes).hexdigest()
    require(manifest_hash == publication["sourceManifest"]["sha256"], "Prepared manifest hash mismatch")

    return {
        "status": "PUBLICATION_RECEIPTS_MATCHED",
        "sourceCommit": commit,
        "worker": worker,
        "publishedAt": publication["date"],
        "publicationSha256": sha256(publication_bytes).hexdigest(),
        "liveEvidenceSha256": live_ref["sha256"],
        "preparedManifestSha256": manifest_hash,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name, description in (
        ("source", "Canonical batch source receipt"),
        ("prepared", "Database owner's frozen source_file_manifest.json"),
        ("publication", "Publisher's final publication JSON for this batch"),
        ("live", "Publisher's live.json referenced by that publication"),
    ):
        parser.add_argument(name, type=Path, help=description)
    args = parser.parse_args()
    try:
        print(json.dumps(match(args.source, args.prepared, args.publication, args.live), indent=2))
    except (OSError, KeyError, ValueError, TypeError, AttributeError) as error:
        parser.exit(1, f"Could not match database receipts: {error}\n")
