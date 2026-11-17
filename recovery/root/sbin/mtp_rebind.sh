#!/sbin/sh
# Wait for FunctionFS endpoints; init binds configfs.

G=${A25_MTP_GADGET_ROOT:-/config/usb_gadget/g1}
CONFIG_DIR=$G/configs/b.1
MTP_EP1=${A25_MTP_EP1:-/dev/usb-ffs/mtp/ep1}
ADB_EP1=${A25_ADB_EP1:-/dev/usb-ffs/adb/ep1}
STATUS_FILE=${A25_MTP_STATUS_FILE:-/tmp/mtp_rebind.status}
controller=$(getprop sys.usb.controller)
[ -n "$controller" ] || controller=musb-hdrc

write_status() {
    printf '%s\n' "$1" > "$STATUS_FILE"
}

mtp_endpoints_ready() {
    [ -e "$MTP_EP1" ] && [ -e "${MTP_EP1%ep1}ep2" ] && [ -e "${MTP_EP1%ep1}ep3" ]
}

mtp_bind_active() {
    [ "$(getprop sys.usb.config)" = "mtp,adb" ] &&
        [ "$(getprop sys.usb.state)" = "mtp,adb" ] &&
        [ "$(cat "$G/UDC" 2>/dev/null)" = "$controller" ] &&
        [ -L "$CONFIG_DIR/f1" ] && [ -L "$CONFIG_DIR/f2" ]
}

adb_bind_active() {
    [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e "$ADB_EP1" ] &&
        [ "$(getprop sys.usb.state)" = adb ] &&
        [ "$(cat "$G/UDC" 2>/dev/null)" = "$controller" ] && [ -L "$CONFIG_DIR/f1" ]
}

fallback_adb() {
    reason=$1
    write_status "fallback:$reason"
    setprop sys.usb.ffs.mtp.ready 0
    setprop sys.usb.config none
    i=0
    while [ "$i" -lt 50 ] && [ "$(getprop sys.usb.state)" != none ]; do
        i=$((i + 1))
        sleep 0.1
    done
    rm -f "$CONFIG_DIR/f1" "$CONFIG_DIR/f2"
    setprop sys.usb.config adb
    i=0
    while [ "$i" -lt 100 ]; do
        adb_bind_active && break
        i=$((i + 1))
        sleep 0.1
    done
    if ! adb_bind_active; then
        write_status "fallback-adb-not-ready:$reason"
        exit 1
    fi
    write_status "fallback-adb-restored:$reason"
    exit 1
}

i=0
write_status waiting-mtp
while [ "$i" -lt 150 ]; do
    [ "$(getprop sys.usb.config)" = "mtp,adb" ] || {
        write_status cancelled
        exit 0
    }
    mtp_endpoints_ready && break
    i=$((i + 1))
    sleep 0.1
done
if ! mtp_endpoints_ready; then
    fallback_adb mtp-endpoint-timeout
fi

i=0
write_status waiting-adb
while [ "$i" -lt 150 ]; do
    [ "$(getprop sys.usb.config)" = "mtp,adb" ] || {
        write_status cancelled
        exit 0
    }
    [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e "$ADB_EP1" ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ "$(getprop sys.usb.ffs.ready)" != 1 ] || [ ! -e "$ADB_EP1" ]; then
    fallback_adb adb-endpoint-timeout
fi

setprop sys.usb.ffs.mtp.ready 1
i=0
write_status waiting-init-bind
while [ "$i" -lt 50 ]; do
    [ "$(getprop sys.usb.config)" = "mtp,adb" ] || {
        write_status cancelled
        exit 0
    }
    mtp_bind_active && break
    i=$((i + 1))
    sleep 0.1
done
if ! mtp_bind_active; then
    fallback_adb init-mtp-bind-timeout
fi

write_status active
