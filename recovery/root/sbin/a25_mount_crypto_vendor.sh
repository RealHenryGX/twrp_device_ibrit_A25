#!/sbin/sh

mounted_source() {
    awk -v target="$2" '$2 == target { print $1; exit }' /proc/mounts
}

ensure_vendor_ro() {
    block="$(readlink -f /dev/block/mapper/vendor)" || return 1
    actual="$(mounted_source "$block" /vendor)"
    if [ "$actual" = "$block" ]; then
        return 0
    fi
    if [ -n "$actual" ]; then
        return 1
    fi
    mount -t ext4 -o ro "$block" /vendor || return 1
    [ "$(mounted_source "$block" /vendor)" = "$block" ]
}

setprop orangefox.a25_vendor.ready 0
sleep 5
while :; do
    if [ -e /dev/block/mapper/vendor ] && ensure_vendor_ro; then
        setprop orangefox.a25_vendor.ready 1
        exit 0
    fi
    sleep 0.2
done
