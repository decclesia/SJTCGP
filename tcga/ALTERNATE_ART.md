# Alternate artwork

The database's star / Switch artwork button cycles the canonical card's `altImages`.
Each image entry may include `label`, `imageVersion`, `release` and `arenaId`.

Arena groups entries with the exact same top-level `name` as artwork variants.
Keep `Number`, effect, statistics, category and name identical to the canonical card;
give the art its own `id`, image and artwork/reprint release. Never append "AA" to
the grouping name or invent a new printed number. Select the artwork in Arena's
deckbuilder variant picker. Leaders still occupy the one-Leader category.

ST1-026-AA is Ippo's ST7 Leader reprint, retaining printed ST1-026 and rarity L.
It is outside ST7's newly numbered support allocation.

After updating a canonical card, run `python tcga/tools/sync_alternate_art.py`.
It refreshes all explicitly mapped variants from the canonical Arena record,
preventing later text/stat updates from leaving old rules on alternate artwork.
