# Database maintenance

Use these tools from a local checkout with Git and Python 3.10 or later. Archive image preparation uses Pillow (the historical replays used Pillow 13.0.0). The full packer reads a trusted local planner seed with Node.js. Keep approved policies, planner data, publication receipts and staging directories outside the repository.

| Change | Check before closing the batch |
|---|---|
| Replace existing artwork | Match the print to its card and AA slot once. Check source hash, JPEG dimensions, orientation, size, path, cache key and the expected file diff. Preserve other variants and fields. |
| Change printed text or stats | Compare the affected fields with the supplied print, including blank versus zero. Check JSON, the corresponding JS mirror and the rendered field when its display changes. |
| Add an identity or change a release | Verify unique IDs, catalogue/text coverage, resource and art references, approved group additions, defaults and saved planner data where affected. Check newly allowed and excluded scopes. |

### Prepare the archive

When transcribing a print, generate `effect_html` with `format_effect(effect, previous_html)` from `format_transcripts.py`. Keep the printed punctuation and casing in `effect`. To list any stored HTML that still needs formatting, run `python tools/database/format_transcripts.py card-text.json`.

```text
python tools/database/prepare_database_batch.py --repo REPO --batch BATCH.json --output ARCHIVE_DELTA
```

Supply a full `baseCommit`. For an existing AA, add an `alternateArt` array with `number`, existing variant `image`, `source` and `sourceSha256`. For a new accessory, use `newAccessories` with `source`, `sourceSha256` and a `record` containing `id`, `set`, `kind`, `name` and the new `image` path. Sources can be relative to the batch file. JPEGs retain their bytes. PNGs use the established progressive JPEG settings. Review the output against the intended canonical diff before committing it.

### Package protected data

```text
python tools/database/database_package.py --repo REPO --commit COMMIT --baseline PRIOR_MANIFEST --baseline-sha256 TRUSTED_DIGEST --policy PRIOR_POLICY --output PACKAGE
python tools/database/pack_database.py --repo REPO --commit COMMIT --planner TRUSTED_PLANNER_JS --approved-policy APPROVED_POLICY --policy-sha256 TRUSTED_DIGEST --output FULL_PACKAGE
```

For a delta, take the prior manifest digest from the verified publication. Assign new card identities to their confirmed release group with `--add-card GROUP CARD_ID`. Declare new accessory memberships with `--add-accessory GROUP ID` and intentional removals with `--remove-path PATH`. The default canonical base is the target's parent. Use `--base-commit` for a multi-commit batch. Changed bytes are read back. Unchanged Git blob IDs carry their previous proofs. Use the full packer for wider membership changes and provide the expected counts for the release. A full incremental rebuild needs a previously verified, intact staging directory, its manifest and its paired report. Use separate output directories for new batches.

ST1 requires the 27 approved accessories. Both packers derive group artwork only from its approved cards, their variants, energy markers and accessories. The protected publisher takes the frozen delta and verifies the current runtime and asset overlay at release time.

### Close the update

```text
python tools/database/match_database_receipts.py SOURCE_RECEIPT PREPARED_MANIFEST PUBLICATION_RECEIPT LIVE_CHECK
```

Use the returned hashes in the existing closeout. Keep each phase's elapsed time in the batch receipt and record external handoff and publication timestamps separately. After the applicable file, access and preservation checks pass, close the batch. Run the optional `replay_batches.py --help` for the private inputs needed to reproduce the ST8, Guard and Red TKG regression checks.
