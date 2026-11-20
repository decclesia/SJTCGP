"""Format printed database effects and audit stored keyword markup without editing the catalogue."""
import argparse
from html import escape, unescape
import json
from pathlib import Path
import re


RED = ("Barrier", "Dual Attack", "Double Damage", "Deflect", "Elusive", "Unblockable",
       "Duel", "Break", "Impact", "Bloom", "Bloomed", "Evolve", "Swap", "Bond", "Deluge",
       "Sub", "Endure", "Crossover", "Gambit", "Scheme", "Conduit", "Scene", "Unique",
       "Critical", "Revenge", "Blocker", "Raid")
TIMINGS = {
    "activate: main", "activate: battle", "your turn", "opponent's turn", "on attack",
    "on play", "on k.o.", "end of your turn", "end of opponent's turn", "end of turn",
    "opponent's attack", "opponent's play", "on block", "on opponent's attack",
}
TERMS = re.compile(
    r"(?P<timing>\[[^\[\]\n]+\])|(?<!\w)(?:"
    r"(?P<green>Clash)|"
    r"(?P<orange>Permanent|Once per [Tt]urn|Threshold(?: (?:\d+|X))?|Accelcharge|Overcharge|"
    r"Charge(?!\s+(?i:phases?)\b)|V (?i:jump))|"
    r"(?P<red>Limit (?:\d+|X)|J-Layer(?: (?:\d+|X))?|" + "|".join(map(re.escape, RED)) + r"))(?!\w)"
)
TAG = re.compile(r'(<[^>]*>)')
SPAN = re.compile(r'<span class="kw kw-(?:red|purple|green|orange)" title="[A-Za-z0-9 .-]+">')


def color_text(text):
    pieces = []
    end = 0
    for token in TERMS.finditer(text):
        value = token[0]
        color = token.lastgroup
        title = value
        if color == "timing":
            parts = [p.strip().lower().replace("’", "'") for p in value[1:-1].split("/")]
            if parts == ["activate: main", "battle"]:
                parts[1] = "activate: battle"
            if any(part not in TIMINGS for part in parts):
                continue
            color, title = "purple", "Timing window"
        elif value.startswith(("Limit ", "Threshold ", "J-Layer ")):
            title = value.split()[0] + " X"
        elif value == "Bloomed":
            title = "Bloom"
        pieces.append(escape(text[end:token.start()]))
        pieces.append(f'<span class="kw kw-{color}" title="{escape(title)}">{escape(value)}</span>')
        end = token.end()
    pieces.append(escape(text[end:]))
    return "".join(pieces).replace("\n", "<br>")


def repair_existing(effect, markup):
    # Keep approved italics and individually styled print exceptions (e.g. Overcharged).
    # Reuse only the catalogue's narrow markup grammar when its full text is current.
    stack = []
    plain = []
    output = []
    for part in TAG.split(markup):
        if part in ("<em>", "<br>") or SPAN.fullmatch(part):
            if part == "<br>":
                plain.append("\n")
            else:
                stack.append("em" if part == "<em>" else "span")
            output.append(part)
        elif part in ("</em>", "</span>"):
            if not stack or stack.pop() != part[2:-1]:
                return None
            output.append(part)
        else:
            if "<" in part:
                return None
            value = unescape(part)
            plain.append(value)
            if "span" in stack or not TERMS.search(value):
                output.append(part)
            else:
                colored = color_text(value)
                # Preserve original entity spelling when no keyword qualified.
                output.append(colored if "<span" in colored else part)
    if stack or "".join(plain) != effect:
        return None
    html = "".join(output)
    html = re.sub(r'<span class="kw kw-orange" title="Charge">Charge</span>(?=\s+(?i:phases?)\b)',
                  "Charge", html)
    # Some older records colored just the word, leaving the printed parameter outside.
    return re.sub(r'(<span class="kw kw-(?:orange|red)" title="[^"]+">(?:Threshold|J-Layer))</span>( (?:\d+|X))\b',
                  r"\1\2</span>", html)


def format_effect(effect, previous_html=None):
    """Return display markup without changing the authoritative effect text."""
    if previous_html is not None:
        repaired = repair_existing(effect, previous_html)
        if repaired is not None:
            return repaired
    return color_text(effect)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogue", type=Path, help="Canonical card-text.json")
    args = parser.parse_args()
    records = json.loads(args.catalogue.read_bytes())
    changed = [key for key, row in records.items()
               if format_effect(row["effect"], row["effect_html"]) != row["effect_html"]]
    print(json.dumps({"cards": len(records), "needsFormatting": changed}, indent=2))
