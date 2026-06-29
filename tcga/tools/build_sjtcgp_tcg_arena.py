from __future__ import annotations

import base64
import json
import math
import re
import shutil
import textwrap
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\User\Documents\Codex\2026-06-20\ta")
ARCHIVE_PATH = ROOT / "outputs" / "SJTCGP_Card_Text_Archive" / "cards-text-archive.json"
SOURCE_CARDS_PATH = ROOT / "outputs" / "SJTCGP_GitHub_Pages_Text_Update" / "cards.json"
CARD_IMAGE_DIR = ROOT / "outputs" / "SJTCGP_GitHub_Pages_Text_Update" / "images"
LOGO_PATH = ROOT / "outputs" / "SJTCGP_GitHub_Pages_Text_Update" / "assets" / "sjtcg-logo.svg"
TOKEN_SOURCE = ROOT / "work" / "tcg-arena-assets-20260629"
TORU_DECK_PATH = ROOT / "outputs" / "Toru_Sample_Deck_Deckbuilder.json"
OUTPUT_ROOT = ROOT / "outputs" / "SJTCGP_TCG_Arena_GitHub_Update"
TCGA_DIR = OUTPUT_ROOT / "tcga"
ASSET_DIR = TCGA_DIR / "assets"
LANDSCAPE_CARD_DIR = ASSET_DIR / "landscape-cards"
BASE_URL = "https://decclesia.github.io/SJTCGP/"
GAME_NAME = "SJTCGP - Shonen Jump Trading Card Game"

CARD_BACK = "tcga/assets/card-back.jpg"
JUMP_CARD_BACK = "tcga/assets/jump-card-back.jpg"
MENU_BACKGROUND = "tcga/assets/menu-background.jpg"
GAME_FILE = "tcga/Game_SJTCGP.json"
CARDS_FILE = "tcga/cards.json"
STARTERS_FILE = "tcga/starterDecks.json"


KEYWORDS = [
    "Activate: Battle",
    "Activate: Main",
    "End of Opponent's Turn",
    "End of your Turn",
    "Opponent's Attack",
    "Opponent's Play",
    "Opponent's Turn",
    "Once per Turn",
    "Double Damage",
    "Dual Attack",
    "On Attack",
    "On Block",
    "On K.O.",
    "On Play",
    "Your Turn",
    "Accelcharge",
    "Overcharge",
    "Permanent",
    "Threshold",
    "V Jump",
    "J-Layer",
    "Limit 1",
    "Barrier",
    "Blocker",
    "Break",
    "Bloom",
    "Bond",
    "Charge",
    "Clash",
    "Critical",
    "Deflect",
    "Duel",
    "Elusive",
    "Evolve",
    "Impact",
    "Raid",
    "Revenge",
    "Swap",
    "Unique",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def to_number(value: str | int | None):
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return value


def split_traits(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"\s*/\s*", value or "") if item.strip()]


def classify_card(card: dict) -> str:
    if card.get("deck_zone") == "JUMP":
        if card.get("life"):
            return "JUMP Leader"
        return "JUMP Unit" if card.get("power") else "JUMP Action"
    if card.get("card_category") == "Leader":
        return "Leader"
    return "Unit" if card.get("power") else "Action"


def face_type(card_type: str) -> str:
    return card_type.upper()


def deck_category(card: dict) -> str:
    if card.get("card_category") == "Leader" and card.get("deck_zone") != "JUMP":
        return "Leader"
    return "JUMP_Deck" if card.get("deck_zone") == "JUMP" else "Main_Deck"


def keyword_list(effect: str) -> list[str]:
    effect_folded = (effect or "").casefold()
    found = []
    for keyword in KEYWORDS:
        if keyword.casefold() in effect_folded:
            found.append(keyword)
    return found


def make_card_entry(card: dict) -> dict:
    card_type = classify_card(card)
    number = card["card_no"]
    if card.get("orientation") == "Landscape":
        image_url = BASE_URL + f"tcga/assets/landscape-cards/{number}.jpg"
    else:
        image_url = BASE_URL + card["image_url"].replace("\\", "/")
    cost = to_number(card.get("cost"))
    sj_cost = to_number(card.get("sj_cost"))
    life = to_number(card.get("life"))
    power = to_number(card.get("power"))
    counter = to_number(card.get("counter"))
    traits = split_traits(card.get("traits", ""))
    front = {
        "name": card.get("name") or number,
        "type": face_type(card_type),
        "cost": cost,
        "image": image_url,
        "isHorizontal": card.get("orientation") == "Landscape",
    }
    if power is not None:
        front["power"] = power
    if sj_cost is not None:
        front["sjCost"] = sj_cost
    return {
        "id": number,
        "face": {"front": front},
        "name": f"{card.get('name') or number} [{number}]",
        "type": deck_category(card),
        "Number": number,
        "Card_Type": card_type,
        "Color": card.get("color", ""),
        "Set": card.get("set", ""),
        "Release": card.get("release", ""),
        "Rarity": card.get("rarity", ""),
        "Cost": cost,
        "SJ_Cost": sj_cost,
        "Life": life,
        "Power": power,
        "Counter": counter,
        "Traits": traits,
        "Keywords": keyword_list(card.get("effect", "")),
        "Effect": card.get("effect", ""),
        "Deck_Zone": card.get("deck_zone", "Main"),
        "Orientation": card.get("orientation", "Portrait"),
        "image": image_url,
    }


def build_landscape_card_assets(archive_cards: list[dict]) -> None:
    """Prepare counter-rotated faces for TCG Arena's horizontal-card renderer."""
    LANDSCAPE_CARD_DIR.mkdir(parents=True, exist_ok=True)
    for card in archive_cards:
        if card.get("orientation") != "Landscape":
            continue
        number = card["card_no"]
        source = CARD_IMAGE_DIR / f"{number}.jpg"
        destination = LANDSCAPE_CARD_DIR / f"{number}.jpg"
        with Image.open(source) as image:
            prepared = image.convert("RGB").transpose(Image.Transpose.ROTATE_90)
            prepared.save(
                destination,
                "JPEG",
                quality=92,
                optimize=True,
                progressive=True,
                subsampling=1,
            )


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [Path(r"C:\Windows\Fonts\arialbd.ttf"), Path(r"C:\Windows\Fonts\impact.ttf")]
        if bold
        else [Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\calibri.ttf")]
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        for x in range(width):
            pixels[x, y] = color
    return image


def fit_center(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, center_x: int, y: int, fill, stroke=0, stroke_fill=None):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    draw.text(
        (center_x - (box[2] - box[0]) / 2, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=stroke_fill,
    )


def make_card_back(path: Path, jump: bool = False) -> None:
    width, height = 716, 1000
    image = vertical_gradient((width, height), (6, 10, 18), (18, 25, 40))
    draw = ImageDraw.Draw(image)
    gold = (202, 154, 44)
    pale_gold = (242, 207, 107)
    ink = (5, 7, 11)
    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=34, outline=gold, width=9)
    draw.rounded_rectangle((48, 48, width - 48, height - 48), radius=26, outline=(104, 79, 25), width=3)
    for offset in range(-height, width, 120):
        draw.line((offset, 0, offset + height, height), fill=(24, 32, 49), width=18)
    draw.ellipse((118, 235, width - 118, 715), outline=(104, 79, 25), width=5)
    draw.ellipse((145, 262, width - 145, 688), outline=gold, width=2)
    title_font = get_font(102, bold=True)
    small_font = get_font(24, bold=True)
    jump_font = get_font(42, bold=True)
    fit_center(draw, "SJTCG", title_font, width // 2, 410, pale_gold, 4, ink)
    draw.line((130, 540, width - 130, 540), fill=gold, width=4)
    fit_center(draw, "SHONEN JUMP", small_font, width // 2, 565, (224, 226, 232))
    fit_center(draw, "TRADING CARD GAME", small_font, width // 2, 603, (224, 226, 232))
    if jump:
        draw.rounded_rectangle((170, 725, width - 170, 802), radius=20, fill=(134, 30, 44), outline=pale_gold, width=3)
        fit_center(draw, "JUMP DECK", jump_font, width // 2, 737, (255, 255, 255), 2, ink)
    else:
        fit_center(draw, "CARD BACK", get_font(30, bold=True), width // 2, 750, (145, 151, 165))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=90, optimize=True, progressive=True)


def make_menu_background(path: Path) -> None:
    width, height = 1800, 1000
    image = vertical_gradient((width, height), (5, 9, 16), (21, 29, 45))
    draw = ImageDraw.Draw(image)
    gold = (202, 154, 44)
    for offset in range(-height, width + height, 180):
        draw.line((offset, 0, offset - 500, height), fill=(29, 39, 58), width=36)
    draw.rectangle((0, height - 170, width, height), fill=(4, 7, 12))
    fit_center(draw, "SJTCG", get_font(220, bold=True), width // 2, 295, (242, 207, 107), 7, (0, 0, 0))
    draw.line((510, 570, width - 510, 570), fill=gold, width=7)
    fit_center(draw, "SHONEN JUMP TRADING CARD GAME", get_font(48, bold=True), width // 2, 610, (232, 234, 240))
    fit_center(draw, "TCG ARENA", get_font(34, bold=True), width // 2, 865, (152, 158, 173))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=88, optimize=True, progressive=True)


def make_generic_energy(path: Path) -> None:
    width, height = 620, 868
    image = vertical_gradient((width, height), (9, 17, 30), (30, 42, 64))
    draw = ImageDraw.Draw(image)
    gold = (202, 154, 44)
    pale = (242, 207, 107)
    draw.rounded_rectangle((22, 22, width - 22, height - 22), radius=32, outline=gold, width=8)
    draw.ellipse((110, 160, width - 110, 560), outline=gold, width=6)
    draw.polygon([(310, 205), (405, 375), (330, 375), (380, 520), (215, 330), (292, 330)], fill=pale)
    fit_center(draw, "SJTCGP", get_font(62, bold=True), width // 2, 600, pale, 3, (0, 0, 0))
    fit_center(draw, "ENERGY MARKER", get_font(32, bold=True), width // 2, 690, (235, 237, 242))
    fit_center(draw, "GENERIC", get_font(24, bold=True), width // 2, 748, (155, 162, 177))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=90, optimize=True, progressive=True)


def compress_image(source: Path, destination: Path, width: int = 620) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = image.convert("RGB")
        target_height = round(image.height * width / image.width)
        image = image.resize((width, target_height), Image.Resampling.LANCZOS)
        image.save(destination, "JPEG", quality=84, optimize=True, progressive=True, subsampling=1)


def marker_entry(marker_id: str, name: str, category: str, face: str, series: str, image_rel: str, marker_type: str) -> dict:
    image_url = BASE_URL + image_rel
    return {
        "id": marker_id,
        "face": {
            "front": {
                "name": name,
                "type": face,
                "cost": None,
                "image": image_url,
                "isHorizontal": False,
            }
        },
        "name": name,
        "type": category,
        "Number": marker_id,
        "Card_Type": marker_type,
        "Color": "",
        "Set": series,
        "Release": "Accessory",
        "Rarity": "Token",
        "Cost": None,
        "SJ_Cost": None,
        "Life": None,
        "Power": None,
        "Counter": 3000 if marker_type == "Guard Token" else None,
        "Traits": [],
        "Keywords": [],
        "Effect": "+3000 Counter during defensive Combo." if marker_type == "Guard Token" else "",
        "Deck_Zone": category,
        "Orientation": "Portrait",
        "image": image_url,
        "isAccessory": True,
    }


def build_markers(cards: dict) -> tuple[dict, list[str]]:
    energy_by_series: dict[str, list[str]] = defaultdict(list)
    sj_by_series: dict[str, list[str]] = defaultdict(list)
    guard_by_series: dict[str, list[str]] = defaultdict(list)
    token_ids: list[str] = []

    groups = [
        (TOKEN_SOURCE / "energy" / "ENERGY", ASSET_DIR / "energy", "Energy_Stack", "ENERGY", "Energy Marker", energy_by_series),
        (TOKEN_SOURCE / "sj-markers" / "SJ Markers", ASSET_DIR / "sj-markers", "SJ_Marker_Pile", "SJ MARKER", "SJ Marker", sj_by_series),
        (TOKEN_SOURCE / "guard-tokens" / "Guard Tokens", ASSET_DIR / "guard-tokens", "Guard_Token_Pile", "GUARD TOKEN", "Guard Token", guard_by_series),
    ]

    for source_dir, destination_dir, category, face, marker_type, map_dict in groups:
        for source in sorted(source_dir.glob("*.png")):
            stem = source.stem.upper()
            if stem.startswith("SJM-"):
                series_match = re.match(r"SJM-([A-Z]+)", stem)
                series = series_match.group(1) if series_match else "GENERIC"
            elif stem.startswith("GT-"):
                series = stem.removeprefix("GT-")
            else:
                series = stem
            destination = destination_dir / f"{stem}.jpg"
            compress_image(source, destination)
            marker_id = f"TOKEN-{stem}"
            rel = destination.relative_to(OUTPUT_ROOT).as_posix()
            readable = stem.replace("SJM-", "SJ Marker ").replace("GT-", "Guard Token ")
            if category == "Energy_Stack":
                readable = f"Energy Marker {series}"
            cards[marker_id] = marker_entry(marker_id, readable, category, face, series, rel, marker_type)
            map_dict[series].append(marker_id)
            token_ids.append(marker_id)

    generic_path = ASSET_DIR / "energy" / "ENERGY-GENERIC.jpg"
    make_generic_energy(generic_path)
    generic_id = "TOKEN-ENERGY-GENERIC"
    cards[generic_id] = marker_entry(
        generic_id,
        "Energy Marker Generic",
        "Energy_Stack",
        "ENERGY",
        "GENERIC",
        generic_path.relative_to(OUTPUT_ROOT).as_posix(),
        "Energy Marker",
    )
    energy_by_series["GENERIC"].append(generic_id)
    token_ids.append(generic_id)

    marker_map = {
        "bySeries": {},
        "notes": {
            "energyFallback": generic_id,
            "automaticAssignment": "The included deck converter assigns exact Set art when available and uses the generic Energy Marker otherwise.",
            "arenaLimitation": "TCG Arena itself cannot dynamically change accessory art after a Leader is selected.",
        },
    }
    all_series = sorted(set(energy_by_series) | set(sj_by_series) | set(guard_by_series))
    for series in all_series:
        marker_map["bySeries"][series] = {
            "energy": energy_by_series.get(series, [generic_id])[0],
            "sjMarkers": sj_by_series.get(series, []),
            "guardToken": guard_by_series.get(series, [None])[0],
        }
    return marker_map, token_ids


def section(
    title: str,
    displayed: str,
    *,
    hidden: str = "no",
    height: str = "SMALL",
    alignment: str = "CENTER",
    horizontal: bool = False,
    group_forbidden: bool = False,
    no_auto_pay_to: bool = True,
    enter_tapped: bool = False,
    enter_spun: bool = False,
    keep_tapped: bool = False,
    quick_actions: bool = False,
    default: bool = False,
    auto_pay_from: bool = False,
) -> dict:
    value = {
        "title": title,
        "isHidden": hidden,
        "height": height,
        "alignment": alignment,
        "opponentAlignment": False,
        "noAutoPayTo": no_auto_pay_to,
        "isHorizontalAllowed": horizontal,
        "isGroupForbidden": group_forbidden,
        "displayedTitle": displayed,
        "noQuickActions": quick_actions,
        "enterTapped": enter_tapped,
        "enterSpun": enter_spun,
        "keepTappedNewTurn": keep_tapped,
        "showHiddenCardInHistory": False,
    }
    if default:
        value["isDefaultSection"] = True
    if auto_pay_from:
        value["autoPayFrom"] = True
    return value


def build_sections() -> dict:
    sections = {
        "Hand": section("Hand", "Hand", hidden="opponent-only", height="DEFAULT", group_forbidden=True, default=True, auto_pay_from=True),
        "Discard": section("Discard", "Drop", height="SMALL", group_forbidden=True, default=True),
        "Deck": section("Deck", "Deck", hidden="yes", height="DEFAULT", alignment="DECK", group_forbidden=True, no_auto_pay_to=False, default=True),
        "Stack": section("Stack", "Action Resolution", height="HUGE", alignment="NONE", group_forbidden=True, no_auto_pay_to=False, default=True),
        "Exile": section("Exile", "Removed from Game", height="SMALL", alignment="NONE", group_forbidden=True, default=True),
        "ExileHidden": section("ExileHidden", "Removed Face-Down", hidden="yes", height="DEFAULT", alignment="NONE", group_forbidden=True, default=True),
        "Sideboard": section("Sideboard", "Sideboard", height="DEFAULT", alignment="NONE", group_forbidden=True, no_auto_pay_to=False, default=True),
        "SJ_Marker_Pile": section("SJ_Marker_Pile", "SJ Marker Pile", height="13", alignment="DECK", group_forbidden=True, no_auto_pay_to=False, keep_tapped=True),
        "SJ_Marker_Area": section("SJ_Marker_Area", "SJ Marker Area", height="8", horizontal=True, enter_tapped=True, keep_tapped=True),
        "Energy_Stack": section("Energy_Stack", "Energy Stack", height="11", alignment="DECK", group_forbidden=True, no_auto_pay_to=False, keep_tapped=True),
        "Guard_Token_Pile": section("Guard_Token_Pile", "Guard Token", height="8", alignment="DECK", group_forbidden=True, no_auto_pay_to=False, keep_tapped=True),
        "JUMP_Deck": section("JUMP_Deck", "JUMP Deck", hidden="yes", height="18", alignment="DECK", group_forbidden=True, no_auto_pay_to=False, keep_tapped=True, quick_actions=True),
        "Leader": section("Leader", "Leader Area", height="18", horizontal=True),
        "Life": section("Life", "Life Area", hidden="yes", height="18", alignment="DECK", group_forbidden=True, quick_actions=True, keep_tapped=True),
        "Field": section("Field", "Field", height="18", horizontal=True),
        "Combo": section("Combo", "Combo Area", height="8", horizontal=True),
        "Energy_Area": section("Energy_Area", "Energy Area", height="8", horizontal=True, keep_tapped=True),
        "Overcharge_Area": section("Overcharge_Area", "Overcharge Area", height="8", horizontal=True, enter_tapped=True, keep_tapped=True),
    }
    return sections


def build_layout() -> dict:
    return {
        "direction": "row",
        "isSymetricalForOpponents": True,
        "style": {"marginTop": "-0.5vh", "gap": "0.6vh"},
        "content": [
            {
                "direction": "column",
                "style": {"width": "14vh"},
                "content": [
                    {"section": "SJ_Marker_Pile", "style": {"height": "13vh"}},
                    {"section": "SJ_Marker_Area", "style": {"height": "8vh", "minHeight": "8vh"}},
                    {"section": "Energy_Stack", "style": {"height": "11vh"}},
                    {"section": "Guard_Token_Pile", "style": {"height": "8vh"}},
                ],
            },
            {
                "direction": "column",
                "style": {"width": "14vh"},
                "content": [{"section": "JUMP_Deck", "style": {"height": "20vh"}}],
            },
            {
                "direction": "column",
                "style": {"width": "14vh"},
                "content": [
                    {"section": "Leader", "style": {"height": "20vh"}},
                    {"section": "Life", "style": {"height": "20vh"}},
                ],
            },
            {
                "direction": "column",
                "style": {"flex": 1},
                "content": [
                    {"section": "Field", "style": {"flex": 1, "minHeight": "23vh"}},
                    {"section": "Combo", "style": {"height": "9vh", "minHeight": "9vh"}},
                    {
                        "direction": "row",
                        "style": {"height": "10vh", "minHeight": "10vh"},
                        "content": [
                            {"section": "Energy_Area", "style": {"flex": 3}},
                            {"section": "Overcharge_Area", "style": {"flex": 1}},
                        ],
                    },
                ],
            },
            {
                "direction": "column",
                "style": {"width": "20vh"},
                "content": [
                    {"section": "Deck", "style": {"height": "19vh"}},
                    {
                        "direction": "row",
                        "style": {"height": "16vh"},
                        "content": [
                            {"section": "Discard", "style": {"flex": 1}},
                            {"section": "Exile", "style": {"flex": 1}},
                        ],
                    },
                ],
            },
        ],
    }


def build_game(token_ids: list[str]) -> dict:
    help_text = """SJTCGP setup and play notes

Deck: 1 Leader, exactly 50 Main Deck cards, and up to 10 JUMP Deck cards. Leaders and SECs are limited to 1; JUMP cards are limited to 1; other cards are normally limited to 4. Leader color locks both decks.

Accessories: Fill Energy Stack and SJ Marker Pile with the art matching your Leader's Set. The included converter does this automatically; when building inside TCG Arena, filter accessories by Set. A generic Energy Marker is provided where no exact Energy art currently exists.

Life: After the opening hand/mulligan, manually place cards from the top of your Deck face-down in Life equal to the Life printed on your Leader.

Energy: The opening charge of 2 is placed automatically at the beginning of each player's first turn. Later charges must be moved manually from Energy Stack: turn 2 charges 3, turn 3 charges 4, and so on. Spent Energy returns to Energy Stack. At end of your turn, move unused Energy to Overcharge Area. At end of the opponent's turn, return unused Overcharged Energy to Energy Stack.

Guard Token: The second player's Guard Token is moved to their hand automatically. It provides +3000 Counter during a defensive Combo.

SJ Markers: When you deal or take damage, you may move up to 1 marker from SJ Marker Pile to SJ Marker Area. Markers enter horizontally. Return spent markers to the pile.

Cards: Units play to Field. Main Deck Actions enter Action Resolution and go to Drop when resolved. JUMP Units and JUMP Actions are played from JUMP Deck to Field; JUMP Actions remain there unless removed by a skill. Removed JUMP Units go to Removed from Game unless stated otherwise.

TCG Arena provides the shared board and deck handling; card skills and rules decisions remain manual."""
    return {
        "name": GAME_NAME,
        "menuBackgroundImage": BASE_URL + MENU_BACKGROUND,
        "defaultRessources": {
            "backgrounds": [BASE_URL + MENU_BACKGROUND],
            "decksUrl": BASE_URL + STARTERS_FILE,
        },
        "customHelp": help_text,
        "cardRotation": "90",
        "cards": {
            "dataUrl": BASE_URL + CARDS_FILE,
            "cardBack": BASE_URL + CARD_BACK,
            "extraCardBacks": {"JUMP_Deck": BASE_URL + JUMP_CARD_BACK},
        },
        "deckBuilding": {
            "mainFilters": ["Color", "Card_Type", "Set", "Release"],
            "formats": [
                {
                    "title": "Standard",
                    "gameplay": "Classic",
                    "customCategories": ["JUMP_Deck", "Energy_Stack", "SJ_Marker_Pile", "Guard_Token_Pile"],
                    "deckRuleset": "Standard",
                }
            ],
            "deckRulesets": {
                "Standard": {
                    "general": {"maxPerCard": 4},
                    "categories": [
                        {"category": "Leader", "min": 1, "max": 1, "maxPerCard": 1},
                        {"category": "Main_Deck", "min": 50, "max": 50},
                        {"category": "JUMP_Deck", "min": 0, "max": 10, "maxPerCard": 1},
                        {"category": "Energy_Stack", "min": 20, "max": 20, "maxPerCard": 20},
                        {"category": "SJ_Marker_Pile", "min": 20, "max": 20, "maxPerCard": 20},
                        {"category": "Guard_Token_Pile", "min": 1, "max": 1, "maxPerCard": 1},
                    ],
                }
            },
        },
        "gameplay": {
            "Classic": {
                "mulligan": {
                    "info": "Opening hand: 5 cards. You may redraw once during setup.",
                    "startingHandSize": 5,
                    "drawNewHand": True,
                    "putSelectionAtBottom": False,
                    "drawNewSelectedCards": False,
                },
                "beforeGameStart": {
                    "initialBoardSetup": {
                        "0": [
                            {
                                "drawFromTop": "Energy_Stack",
                                "count": 2,
                                "destination": "Energy_Area",
                                "waitForPlayerTurn": True,
                            }
                        ],
                        "1": [
                            {
                                "drawFromTop": "Guard_Token_Pile",
                                "count": 1,
                                "destination": "Hand",
                            },
                            {
                                "drawFromTop": "Energy_Stack",
                                "count": 2,
                                "destination": "Energy_Area",
                                "waitForPlayerTurn": True,
                            },
                        ],
                    }
                },
                "newTurn": {
                    "drawOnStart": False,
                    "sharedTurn": False,
                    "firstPlayerTokenName": "",
                    "drawPerTurn": 1,
                },
                "defaultNotes": "Turn / own charge amount: 1→2, 2→3, 3→4, 4→5, 5→6. Later Energy charges are manual.",
                "tokens": token_ids,
                "countersStartingValues": [0, 0],
                "hideFacedDownCards": False,
                "draggableTokens": [],
                "sections": {
                    "customSections": [
                        "SJ_Marker_Pile",
                        "SJ_Marker_Area",
                        "Energy_Stack",
                        "Guard_Token_Pile",
                        "JUMP_Deck",
                        "Leader",
                        "Life",
                        "Field",
                        "Combo",
                        "Energy_Area",
                        "Overcharge_Area",
                    ],
                    "layout": build_layout(),
                    "categoriesAlreadyOnBoard": [
                        "Leader",
                        "JUMP_Deck",
                        "Energy_Stack",
                        "SJ_Marker_Pile",
                        "Guard_Token_Pile",
                    ],
                    "autoPlayFromHand": {
                        "LEADER": "Leader",
                        "UNIT": "Field",
                        "ACTION": "Stack",
                        "JUMP LEADER": "Leader",
                        "JUMP UNIT": "Field",
                        "JUMP ACTION": "Field",
                        "ENERGY": "Energy_Area",
                        "SJ MARKER": "SJ_Marker_Area",
                        "GUARD TOKEN": "Hand",
                    },
                    "autoPlayFromStack": {
                        "LEADER": "Leader",
                        "UNIT": "Field",
                        "ACTION": "Discard",
                        "JUMP LEADER": "Leader",
                        "JUMP UNIT": "Field",
                        "JUMP ACTION": "Field",
                        "ENERGY": "Energy_Area",
                        "SJ MARKER": "SJ_Marker_Area",
                        "GUARD TOKEN": "Hand",
                    },
                    "sectionsDict": build_sections(),
                },
            }
        },
    }


def distribute(total: int, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    base, remainder = divmod(total, len(ids))
    return [
        {"count": base + (1 if index < remainder else 0), "id": marker_id}
        for index, marker_id in enumerate(ids)
        if base + (1 if index < remainder else 0) > 0
    ]


def make_tcga_deck(source: dict, cards: dict, marker_map: dict, title: str | None = None) -> dict:
    raw = source.get("deck", source)
    leader = raw["leader"]
    leader_set = cards[leader].get("Set") or "GENERIC"
    accessories = marker_map["bySeries"].get(leader_set, {})
    energy_id = accessories.get("energy") or "TOKEN-ENERGY-GENERIC"
    sj_ids = accessories.get("sjMarkers") or []
    guard_id = accessories.get("guardToken")
    if not sj_ids:
        # No incorrect cross-series fallback: use an empty category and let the user select art.
        sj_entries = []
    else:
        sj_entries = distribute(20, sj_ids)
    categories = {
        "Main_Deck": [{"count": int(count), "id": card_id} for card_id, count in raw.get("main", {}).items()],
        "Leader": [{"count": 1, "id": leader}],
        "JUMP_Deck": [{"count": int(count), "id": card_id} for card_id, count in raw.get("jump", {}).items()],
        "Energy_Stack": [{"count": 20, "id": energy_id}],
        "SJ_Marker_Pile": sj_entries,
        "Guard_Token_Pile": ([{"count": 1, "id": guard_id}] if guard_id else []),
    }
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "title": title or source.get("name") or f"{leader} Deck",
        "id": f"sjtcgp-{leader.lower()}-sample",
        "game": GAME_NAME,
        "format": ["Standard"],
        "cardCount": sum(item["count"] for values in categories.values() for item in values),
        "createdAt": now,
        "lastModifiedAt": now,
        "deckList": {
            "categoriesOrder": list(categories.keys()),
            "Sideboard": [],
            **categories,
        },
    }


def build_readme(card_count: int, marker_count: int, loader_url: str) -> str:
    return f"""SJTCGP — TCG Arena GitHub Update
========================================

WHAT TO UPLOAD
Upload the included tcga folder to the root of your existing SJTCGP GitHub repository.

Do not replace the existing images folder. The {card_count} card entries in tcga/cards.json point to the card JPGs already hosted there. This package adds only the compressed Energy, SJ Marker, Guard Token, menu-background, and temporary card-back files ({marker_count} accessory entries).

AFTER GITHUB PAGES UPDATES
Open this TCG Arena loader link:
{loader_url}

PACKAGE CONTENTS
- tcga/Game_SJTCGP.json — board, zones, setup, filters, and deck rules
- tcga/cards.json — TCG Arena card list generated from the transcribed archive
- tcga/starterDecks.json — Toru sample deck for immediate testing
- tcga/marker-map.json — exact Set-to-accessory mapping and fallbacks
- tcga/assets/ — compressed accessory art and temporary card backs
- tcga/tools/ — repeatable builders/converters for later database updates

AUTOMATION BOUNDARY
- Automatic: opening two Energy markers on each player's first turn, second-player Guard Token, normal one-card turn draw, Leader/JUMP/accessory placement.
- Manual: later escalating Energy charges (turn 2 charges 3, turn 3 charges 4, etc.), Life setup based on the selected Leader, card skills, and rules decisions.

TCG Arena only exposes a fixed per-turn draw count for custom piles. It cannot safely express the variable 2/3/4/5 Energy schedule, so the package does not substitute an incorrect fixed charge.

TEMPORARY CARD BACK
Replace tcga/assets/card-back.jpg whenever you design the final card back. Replace tcga/assets/jump-card-back.jpg separately if you want a distinct JUMP Deck back. The JSON does not need to change if the filenames stay the same.

CURRENT SETUP ASSUMPTION
The game file uses a 5-card opening hand and lets players redraw once. Life is deliberately manual because Life totals vary by Leader. If the opening-hand rule differs, edit gameplay > Classic > mulligan > startingHandSize in Game_SJTCGP.json.
"""


def copy_tooling() -> None:
    tools_dir = TCGA_DIR / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), tools_dir / "build_sjtcgp_tcg_arena.py")
    converter = ROOT / "work" / "convert_sjtcgp_deck_to_tcga.py"
    if converter.exists():
        shutil.copy2(converter, tools_dir / converter.name)


def build_zip() -> Path:
    zip_path = ROOT / "outputs" / "SJTCGP_TCG_Arena_GitHub_Update.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(OUTPUT_ROOT))
    return zip_path


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    archive_cards = load_json(ARCHIVE_PATH)
    build_landscape_card_assets(archive_cards)
    cards = {card["card_no"]: make_card_entry(card) for card in archive_cards}

    marker_map, token_ids = build_markers(cards)
    leaders = [card for card in archive_cards if card.get("card_category") == "Leader"]
    marker_map["byLeader"] = {
        leader["card_no"]: {
            "set": leader.get("set"),
            **marker_map["bySeries"].get(leader.get("set"), {}),
        }
        for leader in leaders
    }

    make_card_back(ASSET_DIR / "card-back.jpg", jump=False)
    make_card_back(ASSET_DIR / "jump-card-back.jpg", jump=True)
    make_menu_background(ASSET_DIR / "menu-background.jpg")
    shutil.copy2(LOGO_PATH, ASSET_DIR / "sjtcg-logo.svg")

    write_json(TCGA_DIR / "cards.json", cards)
    write_json(TCGA_DIR / "marker-map.json", marker_map)
    game = build_game(token_ids)
    write_json(TCGA_DIR / "Game_SJTCGP.json", game)

    starter_decks = []
    if TORU_DECK_PATH.exists():
        starter_decks.append(make_tcga_deck(load_json(TORU_DECK_PATH), cards, marker_map, "Toru — Calamity Life Loop (Sample)"))
    write_json(TCGA_DIR / "starterDecks.json", starter_decks)

    game_url = BASE_URL + GAME_FILE
    encoded = base64.b64encode(quote(game_url, safe="-_.!~*'()").encode("utf-8")).decode("ascii")
    loader_url = "https://tcg-arena.fr/load/" + encoded
    (OUTPUT_ROOT / "README_UPLOAD.txt").write_text(
        build_readme(len(archive_cards), len(token_ids), loader_url),
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "TCG_ARENA_LINK.txt").write_text(loader_url + "\n", encoding="utf-8")
    copy_tooling()
    zip_path = build_zip()
    print(f"Cards: {len(archive_cards)}")
    print(f"Accessories: {len(token_ids)}")
    print(f"Output: {OUTPUT_ROOT}")
    print(f"ZIP: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print(f"Loader: {loader_url}")


if __name__ == "__main__":
    main()
