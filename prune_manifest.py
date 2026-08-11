#!/usr/bin/env python3
"""Prune omni android-12.1 manifest to recovery-only projects."""
import re
import sys

def prune_projects(path, keep_prefixes, extra_removes=None, drop_lines=None):
    """Keep only <project ...> blocks whose path matches keep_prefixes.
    drop_lines: list of exact stripped lines to drop (e.g. includes)."""
    with open(path) as f:
        lines = f.readlines()

    out = []
    i = 0
    n = len(lines)
    removed = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()
        # drop specific whole lines (include tags etc.)
        if drop_lines and any(stripped == d or (d in stripped and stripped.startswith("<include")) for d in drop_lines):
            removed += 1
            i += 1
            continue
        if stripped.startswith("<project"):
            # collect full block
            block = [line]
            if not stripped.endswith("/>"):
                i += 1
                while i < n and "</project>" not in lines[i]:
                    block.append(lines[i])
                    i += 1
                if i < n:
                    block.append(lines[i])
            # check path
            m = re.search(r'path="([^"]+)"', "".join(block))
            if m:
                p = m.group(1)
                keep = False
                for pref in keep_prefixes:
                    pref = pref.rstrip("/")
                    if p == pref or p.startswith(pref + "/"):
                        keep = True
                        break
                if keep:
                    out.extend(block)
                else:
                    removed += 1
        else:
            out.append(line)
        i += 1
    with open(path, "w") as f:
        f.writelines(out)
    print(f"{path}: removed {removed} blocks")

# ---------- default.xml ----------
# AOSP projects needed for TWRP recovery build
KEEP_AOSP = [
    "build", "bionic", "bootable/recovery",
    "external/avb", "external/boringssl", "external/compiler-rt",
    "external/e2fsprogs", "external/expat", "external/f2fs-tools",
    "external/googletest", "external/libcxx", "external/libcxxabi",
    "external/lz4", "external/protobuf", "external/selinux",
    "external/tinyxml2", "external/zlib", "external/zstd",
    "hardware/libhardware",
    "prebuilts/build-tools", "prebuilts/clang/host/linux-x86",
    "prebuilts/misc", "prebuilts/python/linux-x86/2.7.5",
    "system/extras", "system/libbase", "system/libziparchive",
    "system/logging", "system/tools/mkbootimg",
]
prune_projects("default.xml", KEEP_AOSP)

# remove superproject (repo 2.x will otherwise try to fetch it)
with open("default.xml") as f:
    content = f.read()
content = re.sub(r'\s*<superproject[^/]*/>\s*', "\n", content)
# point AOSP remote at Tsinghua mirror (fast direct, no proxy)
content = content.replace("fetch=\"https://android.googlesource.com\"",
                          "fetch=\"https://mirrors.tuna.tsinghua.edu.cn/git/AOSP\"")
with open("default.xml", "w") as f:
    f.write(content)
print("default.xml: superproject removed, aosp remote -> Tsinghua mirror")

# ---------- omni-default.xml ----------
# keep only: android (omni root), vendor/omni, vendor/interfaces
# drop: omni-private include (ssh, apps), vnc/vim/libncurses, apps
prune_projects(
    "omni-default.xml",
    ["android", "vendor/omni", "vendor/interfaces"],
    drop_lines=["<include name=\"omni-private.xml\" />"],
)

# ---------- omni-aosp.xml ----------
# keep only recovery-relevant omni forks + prebuilts
KEEP_OMNI_AOSP = [
    "build/make", "build/soong", "frameworks/native", "hardware/interfaces",
    "system/core", "system/sepolicy",
    "prebuilts/gas/linux-x86",
    "prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9",
]
prune_projects("omni-aosp.xml", KEEP_OMNI_AOSP)

print("done")
