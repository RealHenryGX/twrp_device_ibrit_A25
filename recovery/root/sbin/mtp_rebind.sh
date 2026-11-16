#!/sbin/sh
# Wait for TWRP's FunctionFS MTP descriptors before binding the configfs
# gadget. The MT6765 recovery uses the MUSB controller.

G=/config/usb_gadget/g1
controller=$(getprop sys.usb.controller)
[ -n "$controller" ] || controller=musb-hdrc

# Recover ADB if the MTP FunctionFS endpoint never appears. The configfs
# init actions rebuild the adb-only function after this property transition.
fallback_adb() {
    setprop sys.usb.ffs.mtp.ready 0
    setprop sys.usb.config none
    sleep 0.2
    rm -f "$G/configs/b.1/f2"
    start adbd
    i=0
    while [ "$i" -lt 100 ]; do
        [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e /dev/usb-ffs/adb/ep1 ] && break
        i=$((i + 1))
        sleep 0.1
    done
    setprop sys.usb.config adb
}

# `none` stops adbd. Start it only after that transition has completed so its
# FunctionFS readiness property and endpoint can drive OrangeFox's ADB bind.
if [ "$(getprop sys.usb.config)" = none ]; then
    start adbd
fi

i=0
while [ "$i" -lt 150 ]; do
    [ -e /dev/usb-ffs/mtp/ep1 ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ ! -e /dev/usb-ffs/mtp/ep1 ]; then
    fallback_adb
    exit 1
fi

i=0
while [ "$i" -lt 150 ]; do
    [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e /dev/usb-ffs/adb/ep1 ] && break
    i=$((i + 1))
    sleep 0.1
done
if [ ! -e /dev/usb-ffs/adb/ep1 ]; then
    fallback_adb
    exit 1
fi

sleep 0.5
echo none > "$G/UDC" 2>/dev/null
rm -f "$G/configs/b.1/f1" "$G/configs/b.1/f2"
echo 0x18d1 > "$G/idVendor"
echo 0x4ee2 > "$G/idProduct"
echo mtp_adb > "$G/configs/b.1/strings/0x409/configuration"
ln -s "$G/functions/ffs.adb" "$G/configs/b.1/f1" || exit 1
ln -s "$G/functions/ffs.mtp" "$G/configs/b.1/f2" || exit 1
echo "$controller" > "$G/UDC" || exit 1
setprop sys.usb.ffs.mtp.ready 1
setprop sys.usb.state "$(getprop sys.usb.config)"
