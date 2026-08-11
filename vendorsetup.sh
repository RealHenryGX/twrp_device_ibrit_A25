#!/usr/bin/env bash
# Legacy compatibility. AndroidProducts.mk is the authoritative lunch list.
add_lunch_combo twrp_A25-user
add_lunch_combo twrp_A25-userdebug
add_lunch_combo twrp_A25-eng

# OrangeFox 12.1 builds break on partitionmanager.cpp: uses AID_MEDIA_RW
# without including <private/android_filesystem_config.h>. Patch at lunch
# time (workflow sources envsetup.sh which sources this file), like the
# ZTE reference tree does for its Unisoc fixes.
_a25_android_top="${ANDROID_BUILD_TOP:-}"
if [[ -z "${_a25_android_top}" ]] && declare -F gettop >/dev/null 2>&1; then
    _a25_android_top="$(gettop)"
fi
if [[ -n "${_a25_android_top}" ]]; then
    python3 "$(dirname "${BASH_SOURCE[0]}")/tools/fix_aid_media_rw.py" || true
else
    echo "A25: cannot locate Android build root, skipping OrangeFox AID_MEDIA_RW patch" >&2
fi
unset _a25_android_top
