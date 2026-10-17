from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
CARDS_PATH = REPO_ROOT / "tcga" / "cards.json"
GAME_PATH = REPO_ROOT / "tcga" / "Game_SJTCGP.json"
SOURCE_IMAGE_DIR = REPO_ROOT / "images"
LANDSCAPE_IMAGE_DIR = REPO_ROOT / "tcga" / "assets" / "landscape-cards"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    cards = load_json(CARDS_PATH)
    game = load_json(GAME_PATH)
    errors: list[str] = []

    # Explicitly declared artwork variants must never retain stale rules/stats.
    metadata_path = REPO_ROOT / "cards.json"
    if metadata_path.is_file():
        for item in load_json(metadata_path):
            for art in item.get("altImages", []):
                variant_id = art.get("arenaId")
                if not variant_id:
                    continue
                original = cards.get(item["number"], {})
                variant = cards.get(variant_id, {})
                if not variant:
                    fail(errors, f"{variant_id}: missing Arena artwork variant.")
                    continue
                for key, value in original.items():
                    if key not in {"id", "image", "face", "Release", "Artwork"} and variant.get(key) != value:
                        fail(errors, f"{variant_id}: {key} differs from canonical card.")
                expected = art["image"]
                if expected not in variant.get("face", {}).get("front", {}).get("image", ""):
                    fail(errors, f"{variant_id}: incorrect artwork path.")
                for key, value in original.get("face", {}).get("front", {}).items():
                    if key != "image" and variant.get("face", {}).get("front", {}).get(key) != value:
                        fail(errors, f"{variant_id}: front {key} differs from canonical card.")

    classic = game["gameplay"]["Classic"]
    ruleset_categories = {
        category["category"]: category
        for category in game["deckBuilding"]["deckRulesets"]["Standard"]["categories"]
    }
    sections = classic["sections"]["sectionsDict"]

    # Supplied Energy art must stay synchronized with both the gallery and mappings.
    energy_path = REPO_ROOT / "energy-markers.json"
    if energy_path.exists():
        energy = load_json(energy_path)
        mapping = load_json(REPO_ROOT / "tcga" / "marker-map.json")
        if len({entry['id'] for entry in energy}) != len(energy):
            fail(errors, "Duplicate Energy Marker gallery identity.")
        for entry in energy:
            marker = cards.get(entry['id'], {})
            asset = REPO_ROOT / entry['image']
            if not asset.exists():
                fail(errors, f"{entry['id']}: missing Energy artwork.")
                continue
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
            expected = 'https://decclesia.github.io/SJTCGP/' + entry['image'] + '?v=' + digest
            if entry['imageVersion'] != digest or marker.get('image') != expected or marker.get('face', {}).get('front', {}).get('image') != expected:
                fail(errors, f"{entry['id']}: stale or mismatched Energy artwork.")
            if marker.get('type') != 'Energy_Stack' or marker.get('Set') != entry['set']:
                fail(errors, f"{entry['id']}: wrong Energy category/series.")
            if entry['id'] not in classic['tokens'] or mapping['bySeries'].get(entry['set'], {}).get('energy') != entry['id']:
                fail(errors, f"{entry['id']}: missing token registration or series mapping.")
        supplied = {entry['set']: entry['id'] for entry in energy}
        for leader, entry in mapping.get('byLeader', {}).items():
            if entry['set'] in supplied and entry['energy'] != supplied[entry['set']]:
                fail(errors, f"{leader}: stale Energy fallback despite supplied series art.")

    if classic["mulligan"]["startingHandSize"] != 6:
        fail(errors, "Opening hand must remain 6.")
    if ruleset_categories["Energy_Stack"]["max"] != 10:
        fail(errors, "Energy Stack maximum must remain 10.")
    if ruleset_categories["SJ_Marker_Pile"]["max"] != 10:
        fail(errors, "SJ Marker Pile maximum must remain 10.")
    if sections["Deck"]["alignment"] != "NONE":
        fail(errors, "Built-in Deck alignment must remain NONE so Arena owns draw/menu interactions.")
    if sections["JUMP_Action_Area"]["isHorizontalAllowed"] is not True:
        fail(errors, "JUMP Action Area must allow horizontal cards.")

    jump_actions = sorted(
        (card for card in cards.values() if card.get("Card_Type") == "JUMP Action"),
        key=lambda card: card["Number"],
    )
    source_images_available = SOURCE_IMAGE_DIR.is_dir()
    for card in jump_actions:
        number = card["Number"]
        front = card.get("face", {}).get("front", {})
        image_url = front.get("image", "")
        if card.get("Orientation") != "Landscape":
            fail(errors, f"{number}: Orientation is not Landscape.")
        if front.get("isHorizontal") is not True:
            fail(errors, f"{number}: face.front.isHorizontal is not true.")
        if f"/landscape-cards/{number}.jpg" not in image_url:
            fail(errors, f"{number}: Arena image does not use its landscape-card asset.")

        source_path = SOURCE_IMAGE_DIR / f"{number}.jpg"
        arena_path = LANDSCAPE_IMAGE_DIR / f"{number}.jpg"
        if source_images_available and not source_path.is_file():
            fail(errors, f"{number}: source image is missing.")
            continue
        if not arena_path.is_file():
            fail(errors, f"{number}: Arena landscape image is missing.")
            continue

        arena_width, arena_height = image_size(arena_path)
        if arena_width >= arena_height:
            fail(errors, f"{number}: Arena asset was not counter-rotated to portrait.")
        if source_images_available:
            source_width, source_height = image_size(source_path)
            if source_width <= source_height:
                fail(errors, f"{number}: source JUMP Action is not physically landscape.")
            if (arena_width, arena_height) != (source_height, source_width):
                fail(errors, f"{number}: Arena dimensions do not match a 90-degree source rotation.")

    if errors:
        print("SJTCGP Arena validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "SJTCGP Arena validation passed: "
        f"{len(jump_actions)} JUMP Actions, Deck interaction alignment NONE, "
        "opening hand 6, Energy 10, SJ Markers 10."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
