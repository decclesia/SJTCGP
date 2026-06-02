# Simple Card Image Database

This is the GitHub-friendly compressed image version.

It contains:

- PUP
- ST1

Each card only needs:

- `number`
- `release`
- `set`
- `image`

Example:

```json
{
  "number": "PUP-001",
  "release": "PUP",
  "set": "CSM",
  "image": "images/PUP-001.jpg"
}
```

## Current set rules

PUP:

- PUP-001 to PUP-003 = CSM
- PUP-004 to PUP-006 = HNI
- PUP-007 to PUP-009 = NRT

ST1:

- ST1-001 to ST1-025 and ST1-126 = CSM
- ST1-026 to ST1-050 = HNI
- ST1-051 to ST1-076 and ST1-127 = NRT
- ST1-077 = SMK
- ST1-101 = JBA

Alternate filenames like `ST1-001 AA` use the same set rule as their base number.

## Run locally

Use a local web server:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```
