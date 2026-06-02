# Simple Card Image Database

This is the simplified version.

Each card only needs:

- `number`
- `release`
- `set`
- `image`

Example:

```json
{
  "number": "SD1-001",
  "release": "SD1",
  "set": "SMK",
  "image": "images/SD1-001.png"
}
```

## Meaning

- `number` = the card number / image filename
- `release` = the batch or product, like `SD1`
- `set` = the printed set code on the card, like `SMK`
- `image` = where the card image is stored

## Add more cards

1. Put the image in the `images` folder.
2. Add a new entry to `cards.json`.
3. Save the file.

## Run locally

Use a local web server:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```
