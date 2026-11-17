#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <android_bootable_recovery checkout>" >&2
    exit 2
fi

recovery_src=$1
patch_file="$(cd -- "$(dirname -- "$0")/../patches" && pwd)/a25-preserve-fbe-on-de-key-failure.patch"

if [[ ! -d "$recovery_src/.git" ]]; then
    echo "not an android_bootable_recovery git checkout: $recovery_src" >&2
    exit 2
fi

if git -C "$recovery_src" apply --reverse --check "$patch_file" 2>/dev/null; then
    echo "A25 FBE recovery patch already applied"
    exit 0
fi

git -C "$recovery_src" apply --check "$patch_file"
git -C "$recovery_src" apply "$patch_file"
echo "Applied A25 FBE recovery patch"
