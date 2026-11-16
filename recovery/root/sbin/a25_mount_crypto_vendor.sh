#!/sbin/sh

VENDOR_BLOCK=${A25_VENDOR_BLOCK:-/dev/block/mapper/vendor}
VENDOR_MOUNT=${A25_VENDOR_MOUNT:-/vendor}
MOUNTS_FILE=${A25_PROC_MOUNTS:-/proc/mounts}

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

# post-fs and recovery startup may both start this oneshot. Preserve a ready
# HAL window when vendor is already mounted; retry only if the mount vanished.
if [ "$(getprop orangefox.a25_vendor.ready)" = 1 ] && ensure_vendor_ro; then
    exit 0
fi

setprop orangefox.a25_vendor.ready 0
while :; do
    if [ -e "$VENDOR_BLOCK" ] && ensure_vendor_ro; then
        setprop orangefox.a25_vendor.ready 1
        exit 0
    fi
    sleep 0.2
done
