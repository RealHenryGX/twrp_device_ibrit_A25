#!/usr/bin/env python3
"""Adapt OrangeFox's modular portrait_hdpi theme to A25's panel aspect ratio."""

from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


SCALE = Decimal("0.8")  # 1080 virtual pixels -> 864 for a 384x854 panel.
NUMBER = re.compile(r"(?<![A-Za-z0-9_.])[+-]?\d+(?:\.\d+)?(?![A-Za-z0-9_.])")
TAG = re.compile(r"<([A-Za-z_][A-Za-z0-9_.:-]*)([^<>]*?)>")
ATTRIBUTE = re.compile(r"(\b(?:x|w|width|dx|dw|name|value)\s*=\s*)(['\"])(.*?)\2")
VARIABLE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")
VARIABLE_TAG = re.compile(r"<variable\b([^<>]*?)/?>")
ATTRIBUTE_VALUE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(['\"])(.*?)\2")


def scale_numbers(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        result = (Decimal(match.group(0)) * SCALE).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return str(int(result))

    return NUMBER.sub(replace, value)


def read_horizontal_variables(xml_files: list[Path]) -> set[str]:
    definitions: dict[str, set[str]] = {}
    horizontal_roots: set[str] = set()
    for path in xml_files:
        source = path.read_text(encoding="utf-8")
        for match in VARIABLE_TAG.finditer(source):
            attributes = {m.group(1): m.group(3) for m in ATTRIBUTE_VALUE.finditer(match.group(1))}
            name = attributes.get("name")
            value = attributes.get("value", "")
            if name:
                definitions.setdefault(name, set()).update(VARIABLE.findall(value))
        for match in TAG.finditer(source):
            for attr in ATTRIBUTE.finditer(match.group(2)):
                key = attr.group(1).strip().split("=")[0].strip()
                if key in ("x", "w", "width", "dx", "dw"):
                    horizontal_roots.update(VARIABLE.findall(attr.group(3)))

    horizontal = set(horizontal_roots)
    changed = True
    while changed:
        changed = False
        for name, references in definitions.items():
            if name not in horizontal and references & horizontal:
                horizontal.add(name)
                changed = True
    return horizontal


def transform_file(path: Path, horizontal_variables: set[str]) -> bool:
    original = path.read_text(encoding="utf-8")

    def transform_tag(match: re.Match[str]) -> str:
        tag_name, attributes = match.group(1), match.group(2)

        def transform_attribute(attr_match: re.Match[str]) -> str:
            key = attr_match.group(1).strip().split("=")[0].strip()
            quote = attr_match.group(2)
            value = attr_match.group(3)
            # Key widths and explicit row offsets share the keyboard artwork's
            # coordinate system. The renderer applies the screen scale to both.
            if tag_name == "keysize":
                return attr_match.group(0)
            if key in ("x", "w", "width", "dx", "dw"):
                value = scale_numbers(value)
            elif tag_name == "variable" and key == "value":
                name_match = re.search(r"\bname\s*=\s*(['\"])(.*?)\1", attributes)
                if name_match and name_match.group(2) in horizontal_variables:
                    value = scale_numbers(value)
            return f"{attr_match.group(1)}{quote}{value}{quote}"

        updated = ATTRIBUTE.sub(transform_attribute, attributes)
        return f"<{tag_name}{updated}>"

    updated = TAG.sub(transform_tag, original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def normalize_list_icon_columns(theme_dir: Path) -> int:
    """Scale literal list icon columns to the A25 virtual canvas."""
    path = theme_dir / "resources/styles.xml"
    original = path.read_text(encoding="utf-8")
    updated = original
    for style_name in ("btn_list", "group_list", "group_list_flat"):
        pattern = rf'(<style name="{style_name}">.*?<iconsize w=")\d+(")'
        updated = re.sub(pattern, rf'\g<1>173\g<2>', updated, count=1, flags=re.DOTALL)
    if updated == original:
        return 0
    path.write_text(updated, encoding="utf-8", newline="\n")
    return 1


def verify(theme_dir: Path) -> None:
    xml_files = sorted(theme_dir.rglob("*.xml"))
    if not xml_files:
        raise ValueError(f"no XML files found under {theme_dir}")

    ui = ET.parse(theme_dir / "ui.xml").getroot()
    resolution = ui.find("./details/resolution")
    if resolution is None or resolution.attrib != {"width": "864", "height": "1920"}:
        raise ValueError("portrait_hdpi/ui.xml must use the A25 864x1920 virtual resolution")

    vars_path = theme_dir / "resources/vars.xml"
    variables = {
        node.attrib.get("name"): node.attrib.get("value")
        for node in ET.parse(vars_path).getroot().iter("variable")
    }
    if variables.get("screen_w") != "864" or variables.get("center_x") != "432":
        raise ValueError("horizontal screen variables were not scaled to 864 pixels")
    styles = (theme_dir / "resources/styles.xml").read_text(encoding="utf-8")
    for style_name in ("btn_list", "group_list", "group_list_flat"):
        match = re.search(
            rf'<style name="{style_name}">(.*?)</style>', styles, re.DOTALL
        )
        if match is None or '<iconsize w="173"' not in match.group(1):
            raise ValueError(f"{style_name} must use the scaled 173-unit icon column")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("theme_dir", type=Path)
    parser.add_argument("--check", action="store_true", help="verify the scaled theme without modifying it")
    args = parser.parse_args()
    theme_dir = args.theme_dir.resolve()
    try:
        if args.check:
            verify(theme_dir)
            print("OrangeFox A25 theme scale checks passed")
            return 0

        ui_path = theme_dir / "ui.xml"
        original_ui = ET.parse(ui_path).getroot()
        resolution = original_ui.find("./details/resolution")
        if resolution is None or resolution.attrib != {"width": "1080", "height": "1920"}:
            raise ValueError("expected an unscaled 1080x1920 portrait_hdpi source theme")

        xml_files = sorted(theme_dir.rglob("*.xml"))
        horizontal_variables = read_horizontal_variables(xml_files)
        changed = sum(transform_file(path, horizontal_variables) for path in xml_files)
        changed += normalize_list_icon_columns(theme_dir)
        verify(theme_dir)
        print(
            f"Scaled {changed} OrangeFox theme XML files; "
            f"{len(horizontal_variables)} horizontal variables; resolution 864x1920"
        )
        return 0
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
