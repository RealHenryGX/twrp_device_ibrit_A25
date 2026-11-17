#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "usage: $0 <android_bootable_recovery checkout>" >&2
    exit 2
fi

recovery_src=$1
patch_file="$(cd -- "$(dirname -- "$0")/../patches" && pwd)/a25-preserve-fbe-on-de-key-failure.patch"
keystore_patch="$(cd -- "$(dirname -- "$0")/../patches" && pwd)/a25-keystore2-rc.patch"

if [[ ! -d "$recovery_src/.git" ]]; then
    echo "not an android_bootable_recovery git checkout: $recovery_src" >&2
    exit 2
fi

apply_or_check() {
    local patch_path=$1
    local label=$2
    if git -C "$recovery_src" apply --reverse --check "$patch_path" 2>/dev/null; then
        echo "$label already applied"
        return
    fi
    git -C "$recovery_src" apply --check "$patch_path"
    git -C "$recovery_src" apply "$patch_path"
    echo "Applied $label"
}

apply_or_check "$patch_file" "A25 FBE recovery patch"
apply_or_check "$keystore_patch" "A25 Keystore2 init patch"
