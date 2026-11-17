#!/sbin/sh

VENDOR_BLOCK=${A25_VENDOR_BLOCK:-/dev/block/mapper/vendor}
VENDOR_MOUNT=${A25_VENDOR_MOUNT:-/vendor}
SYSTEM_BLOCK=${A25_SYSTEM_BLOCK:-/dev/block/mapper/system}
SYSTEM_MOUNT=${A25_SYSTEM_MOUNT:-/system_root}
MOUNTS_FILE=${A25_PROC_MOUNTS:-/proc/mounts}
ADDITIONAL_FSTAB=${A25_ADDITIONAL_FSTAB:-/etc/additional.fstab}
STAGED_ADDITIONAL_FSTAB=${A25_STAGED_ADDITIONAL_FSTAB:-/tmp/a25-additional.fstab}
STATUS_FILE=${A25_CRYPTO_VENDOR_STATUS_FILE:-/tmp/a25_mount_crypto_vendor.status}
SYSTEM_BUILD_PROP=${A25_SYSTEM_BUILD_PROP:-$SYSTEM_MOUNT/system/build.prop}
DATA_FSTAB_ROW='/dev/block/by-name/userdata /data ext4 noatime,nosuid,nodev,noauto_da_alloc,errors=panic,inlinecrypt latemount,wait,check,quota,reservedsize=128M,formattable,checkpoint=block,fileencryption=aes-256-xts:aes-256-cts:v2,keydirectory=/metadata/vold/metadata_encryption,metadata_encryption=aes-256-xts'

is_expected_additional_fstab() {
    [ -f "$1" ] || return 1
    [ "$(wc -l < "$1")" = 1 ] || return 1
    grep -Fxq "$DATA_FSTAB_ROW" "$1"
}

mounted_source() {
    awk -v target="$VENDOR_MOUNT" '$2 == target { print $1; exit }' "$MOUNTS_FILE"
}

ensure_vendor_ro() {
    block="$(readlink -f "$VENDOR_BLOCK")" || return 1
    actual="$(mounted_source)"
    if [ "$actual" = "$block" ]; then
        return 0
    fi
    if [ -n "$actual" ]; then
        return 1
    fi
    mount -t ext4 -o ro "$block" "$VENDOR_MOUNT" || return 1
    [ "$(mounted_source)" = "$block" ]
}

ensure_system_ro() {
    block="$(readlink -f "$SYSTEM_BLOCK")" || return 1
    actual="$(awk -v target="$SYSTEM_MOUNT" '$2 == target { print $1; exit }' "$MOUNTS_FILE")"
    if [ "$actual" = "$block" ]; then
        return 0
    fi
    if [ -n "$actual" ]; then
        return 1
    fi
    mkdir -p "$SYSTEM_MOUNT" || return 1
    mount -t ext4 -o ro "$block" "$SYSTEM_MOUNT" || return 1
    [ "$(awk -v target="$SYSTEM_MOUNT" '$2 == target { print $1; exit }' "$MOUNTS_FILE")" = "$block" ]
}

ensure_additional_fstab() {
    printf '%s\n' "$DATA_FSTAB_ROW" > "$STAGED_ADDITIONAL_FSTAB" || return 1
    chmod 0644 "$STAGED_ADDITIONAL_FSTAB" || return 1
    is_expected_additional_fstab "$STAGED_ADDITIONAL_FSTAB" || return 1
    if is_expected_additional_fstab "$ADDITIONAL_FSTAB"; then
        printf '%s\n' additional-fstab-corrected > "$STATUS_FILE"
        return 0
    fi
    if [ ! -e "$ADDITIONAL_FSTAB" ]; then
        mkdir -p "$(dirname "$ADDITIONAL_FSTAB")" || return 1
        cp "$STAGED_ADDITIONAL_FSTAB" "$ADDITIONAL_FSTAB" || return 1
        chmod 0644 "$ADDITIONAL_FSTAB" || return 1
        is_expected_additional_fstab "$ADDITIONAL_FSTAB" || return 1
        printf '%s\n' additional-fstab-created > "$STATUS_FILE"
        return 0
    fi
    mount -o bind "$STAGED_ADDITIONAL_FSTAB" "$ADDITIONAL_FSTAB" || return 1
    is_expected_additional_fstab "$ADDITIONAL_FSTAB" || return 1
    printf '%s\n' additional-fstab-corrected > "$STATUS_FILE"
}

start_crypto_hals() {
    [ "$(getprop init.svc.servicemanager)" = running ] || return 0
    resetprop_bin=${A25_RESETPROP:-$(command -v resetprop)}
    [ -x "$resetprop_bin" ] || return 1
    [ -f "$SYSTEM_BUILD_PROP" ] || return 1
    for key in ro.build.version.release ro.build.version.sdk ro.build.version.security_patch; do
        value="$(sed -n "s/^$key=//p" "$SYSTEM_BUILD_PROP" | head -n 1)"
        [ -n "$value" ] || return 1
        "$resetprop_bin" -n "$key" "$value" || return 1
    done
    setprop ctl.start vendor.keymaster-4-1
    setprop ctl.start vendor.gatekeeper-1-0
}

prepare_crypto_recovery() {
    ensure_system_ro || {
        printf '%s\n' system-ro-mount-failed > "$STATUS_FILE"
        return 1
    }
    ensure_additional_fstab || {
        printf '%s\n' additional-fstab-overlay-failed > "$STATUS_FILE"
        return 1
    }
    mkdir -p /tmp/a25-keystore2-db || return 1
    chown 1017:1017 /tmp/a25-keystore2-db || return 1
    chmod 0700 /tmp/a25-keystore2-db || return 1
    setprop orangefox.a25_system.ready 1
}

# post-fs and recovery startup may both start this oneshot. Preserve a ready
# HAL window when vendor is already mounted; retry only if the mount vanished.
if [ "$(getprop orangefox.a25_vendor.ready)" = 1 ] && ensure_vendor_ro; then
    prepare_crypto_recovery || exit $?
    start_crypto_hals
    exit $?
fi

setprop orangefox.a25_vendor.ready 0
while :; do
    if [ -e "$VENDOR_BLOCK" ] && ensure_vendor_ro; then
        prepare_crypto_recovery || :
        setprop orangefox.a25_vendor.ready 1
        start_crypto_hals
        exit 0
    fi
    sleep 0.2
done
