"""Replay ST8 AA and RDR Guard offline against frozen evidence in disposable Git checkouts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

ACCESS = Path(__file__).resolve().parent
from database_package import ST1_ACCESSORIES, build_policy, digest, git, index, pack_delta


def read(path):
    return json.loads(path.read_bytes())


def run(tool, *args):
    subprocess.run([sys.executable, "-B", str(ACCESS / tool), *map(str, args)], check=True)


def rejected(message, operation):
    try:
        operation()
    except ValueError as error:
        assert message in str(error), error
    else:
        raise AssertionError("Expected rejection: " + message)


def check_full_package(repo, baseline, policy_file, planner):
    assert digest(baseline.read_bytes()) == "daab99f1a76457e75e1f31654bf43f376b42101250237ecf933be5cd7fd2cd4f"
    expected = read(baseline)
    with TemporaryDirectory(prefix="sjtcgp-full-") as tmp:
        out = Path(tmp)
        subprocess.run([sys.executable, "-B", str(ACCESS / "pack_database.py"), "--repo", str(repo),
                        "--planner", str(planner), "--approved-policy", str(policy_file),
                        "--policy-sha256", "83a89e78662ea27032b3311bce1aeef813b968ecdd4c881be92d8852aa97a227",
                        "--commit", expected["sourceCommit"], "--output", str(out)], check=True,
                       stdout=subprocess.DEVNULL)
        assert read(out / "source_file_manifest.json")["files"] == expected["files"]
        policy = read(out / "database-source/policy.json")
        st1 = index(policy["groups"], "id")["ST1"]
        assert set(st1["accessoryIds"]) == ST1_ACCESSORIES and len(st1["accessoryIds"]) == 27
        excluded = {"TOKEN-SJM-NRT3", "TOKEN-SJM-NRT4"}
        accessories = index(read(out / "database-source/accessories.json"), "id")
        assert all(accessories[n]["image"] not in st1["artPaths"] for n in excluded)
        st1["accessoryIds"][0] = "TOKEN-SJM-NRT3"
        rejected("exactly the approved 27", lambda: build_policy(policy, {}, {}, {}))
        print("Full Red TKG: 1,866 rows match, 27 approved ST1 accessories, both excluded images absent; "
              "same-count ID substitution rejected", flush=True)


def replay(repo, root, batch, receipt_file, prior_dir, prior_sha, spec, additions=()):
    receipt = read(batch / receipt_file)
    files = {r["path"]: r for r in receipt["changedFiles"]}
    commit, base = receipt["sourceCommit"], receipt["baseCommit"]
    args_file = root / "batch.json"
    args_file.write_text(json.dumps(dict(baseCommit=base, **spec)), encoding="utf-8")
    clone = root / "checkout"
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    # Share read-only objects directly. A local clone of a shallow archive may repack its history.
    objects = git(repo, "rev-parse", "--path-format=absolute", "--git-path", "objects").decode().strip()
    (clone / ".git/objects/info/alternates").write_bytes((objects + "\n").encode())
    shallow = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "shallow").decode().strip())
    if shallow.is_file():
        shutil.copyfile(shallow, clone / ".git/shallow")
    git(clone, "config", "core.autocrlf", "true")
    git(clone, "sparse-checkout", "set", "--no-cone", *["/" + name for name in files])
    git(clone, "checkout", "-q", "--detach", base)
    archive = root / "archive"
    prepare = ("prepare_database_batch.py", "--repo", clone, "--batch", args_file, "--output", archive)
    run(*prepare)
    run(*prepare)  # Retrying a completed prepare compares and preserves the original output.
    assert {p.relative_to(archive).as_posix() for p in archive.rglob("*") if p.is_file()} == files.keys()
    for name in files:
        target = clone / name
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(archive / name, target)
    git(clone, "add", "--", *files)
    assert set(git(clone, "diff", "--cached", "--name-only").decode().splitlines()) == files.keys()
    tree = git(clone, "write-tree").decode().strip()
    assert tree == git(clone, "rev-parse", commit + "^{tree}").decode().strip()
    for name, row in files.items():
        body = git(clone, "show", f"{tree}:{name}")
        assert digest(body) == row["sha256"] and len(body) == row["bytes"], name

    delta = root / "package"
    prior = prior_dir / "source_file_manifest.json"
    policy = prior_dir / "protected-delta/policy.json"
    pack = ["database_package.py", "--repo", clone, "--commit", commit, "--baseline", prior,
            "--baseline-sha256", prior_sha, "--policy", policy, "--output", delta]
    for group, item in additions:
        pack.extend(["--add-accessory", group, item])
    run(*pack)
    expected = read(batch / "source_file_manifest.json")
    actual = read(delta / "source_file_manifest.json")
    assert actual["sourceCommit"] == commit and actual["baseCommit"] == base
    assert actual["baselineManifestSha256"] == prior_sha
    assert actual["files"] == expected["files"] and actual["changedFiles"] == sorted(expected["changedFiles"])
    changed = set(actual["changedFiles"])
    staged = delta / "protected-delta"
    assert {p.relative_to(staged).as_posix() for p in staged.rglob("*") if p.is_file()} == changed
    for rel in changed:
        assert (staged / rel).read_bytes() == (batch / "protected-delta" / rel).read_bytes()
    before = index(read(policy)["groups"], "id")
    after = index(read(staged / "policy.json")["groups"], "id") if "policy.json" in changed else before
    assert set(after["ST1"]["accessoryIds"]) == ST1_ACCESSORIES and after["ST1"] == before["ST1"]
    if additions:
        assert [k for k in after if after[k] != before[k]] == ["ST8"]
        assert set(after["ST8"]["accessoryIds"]) - set(before["ST8"]["accessoryIds"]) == {"TOKEN-GT-RDR"}
        assert set(after["ST8"]["artPaths"]) - set(before["ST8"]["artPaths"]) == {spec["newAccessories"][0]["record"]["image"]}
        negative = root / "rejected"
        rejected("Hash mismatch", lambda: pack_delta(clone, commit, prior, "0" * 64, policy, negative))
        rejected("Missing explicit allocation", lambda: pack_delta(clone, commit, prior, prior_sha, policy, negative))
        rejected("Unexpected removals", lambda: pack_delta(clone, commit, prior, prior_sha, policy,
                 negative, additions, removals=["cards.json"]))
        assert not negative.exists()
    print(f"{batch.name}: {len(files)} archive files, exact full Git tree, {len(changed)} protected files, "
          f"{len(actual['files']) - len(changed)} retained rows", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "st8", "st8-prior", "guard", "guard-prior", "full-manifest", "full-policy", "planner"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        parser.error("Run with assertions enabled")
    aa = read(args.st8 / "artwork-receipt.json")
    aa_spec = dict(alternateArt=[dict(number=e["number"], image=e["path"], source=str(args.st8.resolve() / (e["number"] + "-AA.png")),
                                     sourceSha256=e["sourceSha256"]) for e in aa["entries"]])
    ex10 = args.guard_prior.resolve()
    guard = read(args.guard / "source-receipt.json")["artFiles"][0]
    guard_spec = dict(newAccessories=[dict(source=str(ex10 / "normalized" / guard["path"]),
        sourceSha256=guard["sha256"], record=dict(id="TOKEN-GT-RDR", set="RDR", kind="guard",
                                                 name="Guard Token RDR", image=guard["path"]))])
    with TemporaryDirectory(prefix="sjtcgp-aa-") as tmp:
        replay(args.repo, Path(tmp), args.st8, "artwork-receipt.json", args.st8_prior,
               "e830db18f0a0c21a009677ca0047eae1adcc4a1490f4df6fe9a182a18efbaff6", aa_spec)
    with TemporaryDirectory(prefix="sjtcgp-guard-") as tmp:
        replay(args.repo, Path(tmp), args.guard, "source-receipt.json", ex10,
               "78ff8b6fc0b8954995b37be5a9ef41801b3144fccac3458758ff95959daf582a", guard_spec,
               [("ST8", "TOKEN-GT-RDR")])
    check_full_package(args.repo, args.full_manifest, args.full_policy, args.planner)
