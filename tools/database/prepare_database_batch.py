"""Prepare archive files from approved artwork replacements and accessory additions. Offline."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from time import monotonic

from PIL import Image

from database_package import art_path, digest, encode, git, index, install_output, require

MIRRORS = {
    "cards": ("SJTCG_CARD_DATA", "index.html"),
    "accessories": ("SJTCG_ACCESSORIES", "energy.html"),
}


def prepare_image(change, batch_dir, out, rel):
    source = (batch_dir / change["source"]).read_bytes()
    require(digest(source) == change["sourceSha256"], f"Supplied art hash differs: {rel}")
    # Read and convert the same frozen bytes that were checked.
    with Image.open(BytesIO(source)) as image:
        original_size = image.size
        source_format = image.format
        image.verify()
    target = out / art_path(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    require(not target.exists(), f"Two changes write {rel}")
    if source_format == "JPEG":
        target.write_bytes(source)
    else:
        require(source_format == "PNG", f"Expected PNG or JPEG: {rel}")
        with Image.open(BytesIO(source)) as original:
            rgb = original.convert("RGB")
            for quality in range(84, 59, -2):
                buffer = BytesIO()
                rgb.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=1)
                if buffer.tell() <= 500_000:
                    target.write_bytes(buffer.getvalue())
                    break
            else:
                raise ValueError(f"Oversize JPEG: {rel}")
    with Image.open(target) as image:
        require(image.format == "JPEG" and image.size == original_size, f"Changed image dimensions: {rel}")
        image.verify()
    body = target.read_bytes()
    require(len(body) <= 500_000, f"Oversize JPEG: {rel}")
    return digest(body)[:12]


def working_bytes(repo, commit, path):
    return git(repo, "cat-file", "--filters", "--path=" + path, f"{commit}:{path}")


def line_endings(body, reference):
    return body.replace(b"\n", b"\r\n") if b"\r\n" in reference else body


def write_catalogue(out, repo, base, name, records):
    variable, html_name = MIRRORS[name]
    encoded = encode(records)
    mirror = name + "-data.js"
    for path, body in ((name + ".json", encoded),
                       (mirror, b"window." + variable.encode() + b" = " + encoded.rstrip(b"\n") + b";\n")):
        (out / path).write_bytes(line_endings(body, working_bytes(repo, base, path)))
    html = working_bytes(repo, base, html_name)
    version = digest((out / mirror).read_bytes())[:12].encode()
    pattern = rb'(?<=")' + re.escape(mirror.encode()) + rb'\?v=[^"\s]+'
    updated, count = re.subn(pattern, mirror.encode() + b"?v=" + version, html)
    require(count == 1, f"Expected one versioned {mirror} in {html_name}")
    (out / html_name).write_bytes(updated)


def prepare(repo, spec_file, destination):
    spec = json.loads(spec_file.read_bytes())
    require(set(spec) <= {"baseCommit", "alternateArt", "newAccessories"}, "Unknown batch operation")
    base = spec["baseCommit"]
    require(re.fullmatch("[0-9a-f]{40}", base) and git(repo, "rev-parse", base + "^{commit}").decode().strip() == base,
            "Invalid base commit")
    require(spec.get("alternateArt") or spec.get("newAccessories"), "Empty batch")
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as tmp:
        out = Path(tmp) / "output"
        out.mkdir()
        if spec.get("alternateArt"):
            records = json.loads(git(repo, "show", f"{base}:cards.json"))
            by_id = index(records, "number")
            for change in spec["alternateArt"]:
                card = by_id[change["number"]]
                variant = index(card.get("altImages", []), "image")[change["image"]]
                variant["imageVersion"] = prepare_image(change, spec_file.parent, out, variant["image"])
            write_catalogue(out, repo, base, "cards", records)
        if spec.get("newAccessories"):
            records = json.loads(git(repo, "show", f"{base}:accessories.json"))
            by_id = index(records, "id")
            for change in spec["newAccessories"]:
                record = change["record"].copy()
                require(set(record) == {"id", "set", "kind", "name", "image"} and
                        all(isinstance(v, str) and v for v in record.values()), "Incomplete accessory")
                rel = art_path(record["image"])
                require(record["id"] not in by_id, f"Existing accessory ID: {record['id']}")
                require(not git(repo, "ls-tree", "-z", base, "--", ":(literal)" + rel),
                        f"Existing archive artwork: {rel}")
                record["imageVersion"] = prepare_image(change, spec_file.parent, out, rel)
                by_id[record["id"]] = record
            write_catalogue(out, repo, base, "accessories", sorted(by_id.values(), key=lambda r: r["id"]))
        install_output(out, destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "batch", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    started = monotonic()
    prepare(args.repo, args.batch, args.output)
    print(json.dumps({"phase": "archive-prepare", "output": str(args.output),
                      "elapsedSeconds": round(monotonic() - started, 3)}))
