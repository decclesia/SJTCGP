SJTCGP ST3 Pink Cardcaptor Sakura GitHub Update
================================================

Upload the contents of this folder to the root of the existing SJTCGP GitHub Pages repository. Preserve the included folder structure and replace files with matching names.

This is a minimal update package. It contains only files changed or added for this release:

DATABASE ROOT FILES
- cards.json
- cards-data.js
- card-text.json
- card-text-data.js
- BUILD_CHECKS.txt

NEW CARD IMAGES
- images/ST3-081.jpg through images/ST3-100.jpg
- images/PUP-054.jpg through images/PUP-056.jpg

TCG ARENA DATA
- tcga/cards.json
- tcga/marker-map.json
- tcga/Game_SJTCGP.json
- tcga/tools/build_sjtcgp_tcg_arena.py

NEW TCG ARENA ASSETS
- tcga/assets/guard-tokens/GT-CCS.jpg
- tcga/assets/sj-markers/SJM-CCS1.jpg
- tcga/assets/sj-markers/SJM-CCS2.jpg
- tcga/assets/landscape-cards/ST3-100.jpg
- tcga/assets/landscape-cards/PUP-056.jpg

NOTES
- The website database contains 603 cards after this update.
- ST3-100 and PUP-056 are landscape JUMP Actions and use counter-rotated Arena assets so they appear upright on the field.
- ST3-099 and PUP-055 are JUMP Units and intentionally have no Counter field.
- JUMP Actions intentionally have no Traits.
- CCS has a Guard Token and two SJ Markers. No CCS Energy Marker was supplied, so Arena uses the existing generic Energy fallback for CCS decks.
- The local project planner has been updated separately and is not part of the GitHub upload package.
