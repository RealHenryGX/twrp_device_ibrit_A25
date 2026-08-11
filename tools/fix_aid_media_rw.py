#!/usr/bin/env python3
"""OrangeFox 12.1 build fix: partitionmanager.cpp uses AID_MEDIA_RW
(defined in <private/android_filesystem_config.h>) but the OrangeFox
fork never includes that header -> 'use of undeclared identifier'.

Idempotent: only patches when AID_MEDIA_RW is used AND the header is
missing. Safe for TeamWin trees (they don't use AID_MEDIA_RW at all).
Run from vendorsetup.sh at lunch time, like the ZTE reference tree does.
"""
import os
import sys

TARGET = os.path.join(
    os.environ.get("ANDROID_BUILD_TOP", ""),
    "bootable/recovery/partitionmanager.cpp",
)

def main() -> int:
    if not os.path.isfile(TARGET):
        print(f"fix_aid_media_rw: {TARGET} not found, skipping", file=sys.stderr)
        return 0
    with open(TARGET, encoding="utf-8", errors="replace") as f:
        src = f.read()

    if "AID_MEDIA_RW" not in src:
        print("fix_aid_media_rw: no AID_MEDIA_RW usage, nothing to do")
        return 0
    if "android_filesystem_config.h" in src:
        print("fix_aid_media_rw: header already included, nothing to do")
        return 0

    # Insert the include after the last system include (before first "using"/code)
    marker = "#include <linux/fs.h>"
    if marker in src:
        src = src.replace(
            marker,
            marker + '\n#include <private/android_filesystem_config.h>',
            1,
        )
    else:
        # fallback: insert after the last #include line
        lines = src.splitlines(keepends=True)
        last_inc = max(i for i, l in enumerate(lines) if l.strip().startswith("#include"))
        lines.insert(last_inc + 1, "#include <private/android_filesystem_config.h>\n")
        src = "".join(lines)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)
    print("fix_aid_media_rw: patched partitionmanager.cpp with android_filesystem_config.h")
    return 0

if __name__ == "__main__":
    sys.exit(main())
