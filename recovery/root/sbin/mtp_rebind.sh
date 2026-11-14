#!/sbin/sh
# Wait for TWRP's FunctionFS MTP descriptors before binding the configfs
# gadget. The MT6765 recovery uses the MUSB controller.

G=/config/usb_gadget/g1
controller=$(getprop sys.usb.controller)
[ -n "$controller" ] || controller=musb-hdrc

i=0
while [ "$i" -lt 150 ]; do
    [ -e /dev/usb-ffs/mtp/ep1 ] && break
    i=$((i + 1))
    sleep 0.1
done
[ -e /dev/usb-ffs/mtp/ep1 ] || exit 1

i=0
while [ "$i" -lt 150 ]; do
    [ "$(getprop sys.usb.ffs.ready)" = 1 ] && [ -e /dev/usb-ffs/adb/ep1 ] && break
    i=$((i + 1))
    sleep 0.1
done
[ -e /dev/usb-ffs/adb/ep1 ] || exit 1

sleep 0.5
echo none > "$G/UDC" 2>/dev/null
rm -f "$G/configs/b.1/f1" "$G/configs/b.1/f2"
echo 0x18d1 > "$G/idVendor"
echo 0x4ee2 > "$G/idProduct"
echo mtp_adb > "$G/configs/b.1/strings/0x409/configuration"
ln -s "$G/functions/ffs.adb" "$G/configs/b.1/f1" || exit 1
ln -s "$G/functions/ffs.mtp" "$G/configs/b.1/f2" || exit 1
echo "$controller" > "$G/UDC" || exit 1
setprop sys.usb.state "$(getprop sys.usb.config)"
