# SJTCGP Card Database

Canonical card metadata, transcriptions and artwork for the SJTCGP database and local deckbuilder. The automated simulator is maintained separately.

## Current publishing

`main` is the canonical source archive. GitHub Pages serves the separate `database-gateway` branch, which links to the protected database. Publishing new protected catalogue data uses the coordinated database-source workflow; pushing this source archive alone does not deploy the protected database or simulator.

## Updating the database

See the [maintenance tools and update checks](tools/database/README.md) for artwork preparation, protected packaging and receipt matching.

## Arena retired

TCG Arena integration was retired on 16 November 2026. Its configuration, generated catalogue, starter decks, conversion/build tools, rotated landscape exports and unused Arena-only assets have been removed from the current source tree.

The remaining `tcga/assets/energy`, `tcga/assets/guard-tokens` and `tcga/assets/sj-markers` files are shared database artwork. Their legacy directory names are retained to preserve current URLs, metadata, planner provenance and protected art allowlists. Keep every asset referenced by `accessories.json` or `energy-markers.json`.

The database's normal card views, AA selection, filters, deck validation, saving and deck-image export remain supported. Simulator card data, scripts, access, ownership and deployment are not changed by this cleanup.

Historical commits and `BUILD_CHECKS.txt` remain as project provenance. They can describe retired Arena behavior and are not current deployment instructions. Historical source pins are intentionally retained.
