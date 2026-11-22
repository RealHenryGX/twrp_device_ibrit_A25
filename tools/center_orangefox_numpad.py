#!/usr/bin/env python3
"""Center the 1080-wide OrangeFox numpad artwork and touch rows on A25."""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keyboard", type=Path)
    parser.add_argument("artwork_dir", type=Path)
    args = parser.parse_args()

    keyboard = args.keyboard.read_text(encoding="utf-8")
    start = keyboard.index('<template name="keyboardnum">')
    end = keyboard.index("</template>", start)
    numeric = keyboard[start:end]
    if '<placement x="0"' not in numeric or 'height="160" width="212"' not in numeric:
        parser.error("unexpected numeric keyboard size or placement")
    numeric, count = re.subn(r'(key0[15]=")225:(")', r'\g<1>117:\2', numeric)
    if count != 8:
        parser.error(f"expected eight numeric row spacers, found {count}")

    artwork = sorted(args.artwork_dir.glob("key_num_*.svg"))
    if not artwork:
        parser.error("no numeric keyboard artwork found")
    updated = {}
    for path in artwork:
        svg = path.read_text(encoding="utf-8")
        svg, count = re.subn(r'viewBox="0 0 1080 645"', 'viewBox="108 0 864 645"', svg)
        if count != 1:
            parser.error(f"unexpected numeric keyboard viewBox in {path}")
        updated[path] = svg

    args.keyboard.write_text(keyboard[:start] + numeric + keyboard[end:], encoding="utf-8", newline="\n")
    for path, svg in updated.items():
        path.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Centered four touch rows and {len(updated)} numeric keyboard backgrounds")


if __name__ == "__main__":
    main()
