from __future__ import annotations

import json
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

    classic = game["gameplay"]["Classic"]
    ruleset_categories = {
        category["category"]: category
        for category in game["deckBuilding"]["deckRulesets"]["Standard"]["categories"]
    }
    sections = classic["sections"]["sectionsDict"]

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
