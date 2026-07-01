from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


GAME_NAME = "SJTCGP - Shonen Jump Trading Card Game"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def distribute(total: int, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    base, remainder = divmod(total, len(ids))
    return [
        {"count": base + (1 if index < remainder else 0), "id": marker_id}
        for index, marker_id in enumerate(ids)
        if base + (1 if index < remainder else 0)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an SJTCGP website deck export into a TCG Arena deck file."
    )
    parser.add_argument("deck", type=Path, help="SJTCGP deckbuilder JSON export")
    parser.add_argument("--output", type=Path, help="Destination JSON file")
    parser.add_argument(
        "--tcga-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Folder containing tcga/cards.json and marker-map.json",
    )
    args = parser.parse_args()

    source = read_json(args.deck)
    raw = source.get("deck", source)
    cards = read_json(args.tcga_dir / "cards.json")
    marker_map = read_json(args.tcga_dir / "marker-map.json")
    leader = raw["leader"]
    if leader not in cards:
        raise SystemExit(f"Leader {leader} is not present in the TCG Arena card database.")

    leader_set = cards[leader].get("Set", "GENERIC")
    accessories = marker_map.get("bySeries", {}).get(leader_set, {})
    energy_id = accessories.get("energy") or marker_map["notes"]["energyFallback"]
    sj_ids = accessories.get("sjMarkers") or []
    guard_id = accessories.get("guardToken")

    categories = {
        "Main_Deck": [{"count": int(count), "id": card_id} for card_id, count in raw.get("main", {}).items()],
        "Leader": [{"count": 1, "id": leader}],
        "JUMP_Deck": [{"count": int(count), "id": card_id} for card_id, count in raw.get("jump", {}).items()],
        "Energy_Stack": [{"count": 10, "id": energy_id}],
        "SJ_Marker_Pile": distribute(8, sj_ids),
        "Guard_Token_Pile": ([{"count": 1, "id": guard_id}] if guard_id else []),
    }

    missing = [
        card_id
        for category in ("Main_Deck", "Leader", "JUMP_Deck")
        for item in categories[category]
        for card_id in [item["id"]]
        if card_id not in cards
    ]
    if missing:
        raise SystemExit("Cards missing from the TCG Arena database: " + ", ".join(sorted(set(missing))))

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    title = source.get("name") or f"{leader} Deck"
    output = {
        "title": title,
        "id": str(uuid.uuid4()),
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

    destination = args.output or args.deck.with_name(args.deck.stem + "_TCG_Arena.json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    if not sj_ids:
        print(f"Warning: no SJ Marker art is mapped for {leader_set}; select it in TCG Arena.")
    if not guard_id:
        print(f"Warning: no Guard Token art is mapped for {leader_set}; select it in TCG Arena.")


if __name__ == "__main__":
    main()
