#!/sbin/sh
# Wait for TWRP's FunctionFS MTP descriptors before binding the configfs
# gadget. The MT6765 recovery uses the MUSB controller.

G=${A25_MTP_GADGET_ROOT:-/config/usb_gadget/g1}
MTP_EP1=${A25_MTP_EP1:-/dev/usb-ffs/mtp/ep1}
ADB_EP1=${A25_ADB_EP1:-/dev/usb-ffs/adb/ep1}
STATUS_FILE=${A25_MTP_STATUS_FILE:-/tmp/mtp_rebind.status}
controller=$(getprop sys.usb.controller)
[ -n "$controller" ] || controller=musb-hdrc

write_status() {
    printf '%s\n' "$1" > "$STATUS_FILE"
}

# Restore adb-only gadget after any MTP startup or bind failure.
fallback_adb() {
    write_status "fallback:$1"
    setprop sys.usb.ffs.mtp.ready 0
    setprop sys.usb.config none
    i=0
    while [ "$i" -lt 50 ] && [ "$(getprop sys.usb.state)" != none ]; do
        i=$((i + 1))
        sleep 0.1
    done
    rm -f "$G/configs/b.1/f2"
    setprop sys.usb.config adb
    i=0
    while [ "$i" -lt 100 ]; do
        [ "$(getprop sys.usb.ffs.ready)" = 1 ] &&
            [ -e "$ADB_EP1" ] &&
            [ "$(getprop sys.usb.state)" = adb ] && break
        i=$((i + 1))
        sleep 0.1
    done
    if [ "$(getprop sys.usb.ffs.ready)" != 1 ] || [ ! -e "$ADB_EP1" ]; then
        write_status fallback-adb-not-ready
        exit 1
    fi
    if [ "$(getprop sys.usb.ffs.ready)" != 1 ] ||
       [ ! -e "$ADB_EP1" ] ||
       [ "$(getprop sys.usb.state)" != adb ]; then
        write_status fallback-adb-bind-failed
        exit 1
    fi
    write_status fallback-adb-restored
}

i=0
write_status waiting-mtp
while [ "$i" -lt 150 ]; do
    [ -e "$MTP_EP1" ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ ! -e "$MTP_EP1" ]; then
    fallback_adb mtp-endpoint-timeout
    exit 1
fi

i=0
write_status waiting-adb
while [ "$i" -lt 150 ]; do
    [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e "$ADB_EP1" ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ "$(getprop sys.usb.ffs.ready)" != 1 ] || [ ! -e "$ADB_EP1" ]; then
    fallback_adb adb-endpoint-timeout
    exit 1
fi

write_status binding
if ! echo none > "$G/UDC" 2>/dev/null; then
    fallback_adb udc-unbind-failed
    exit 1
fi
rm -f "$G/configs/b.1/f1" "$G/configs/b.1/f2"
if ! echo 0x18d1 > "$G/idVendor" ||
   ! echo 0x4ee2 > "$G/idProduct" ||
   ! echo mtp_adb > "$G/configs/b.1/strings/0x409/configuration" ||
   ! ln -s "$G/functions/ffs.adb" "$G/configs/b.1/f1" ||
   ! ln -s "$G/functions/ffs.mtp" "$G/configs/b.1/f2" ||
   ! echo "$controller" > "$G/UDC"; then
    fallback_adb configfs-bind-failed
    exit 1
fi
setprop sys.usb.ffs.mtp.ready 1
setprop sys.usb.state "$(getprop sys.usb.config)"
write_status active
