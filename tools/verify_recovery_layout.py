#!/usr/bin/env python3
"""Static checks for the A25 recovery ramdisk.

These checks intentionally validate only facts that are required before a
device flash/test cycle: the MTK USB gadget ownership, the metadata block
alias used by FBE, and the recovery-side Keymaster/Gatekeeper payload.
"""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
RAMDISK = ROOT / "recovery" / "root"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        fail(f"missing or empty: {path.relative_to(ROOT)}")


def main() -> int:
    fstab = (ROOT / "recovery.fstab").read_text(encoding="utf-8")
    usb_rc = (RAMDISK / "init.recovery.usb.rc").read_text(encoding="utf-8")

    metadata = re.search(r"^/metadata\s+\S+\s+([^\s]+)", fstab, re.MULTILINE)
    if not metadata or not metadata.group(1).endswith("/md_udc"):
        fail("/metadata must use /dev/block/by-name/md_udc")

    # OrangeFox 12.1 already imports and owns the configfs USB state machine
    # from /system/etc/init/hw/init.rc. The device-tree compatibility import
    # must stay free of USB actions; two owners create an ffs.adb bind loop.
    if any(token in usb_rc for token in (
        "mount configfs none /config",
        "mount functionfs adb /dev/usb-ffs/adb",
        "setprop sys.usb.config adb",
        "write /config/usb_gadget/g1/UDC",
    )):
        fail("device-tree USB rc must not duplicate OrangeFox configfs ownership")
    require(RAMDISK / "init.recovery.mt6765.rc")
    mt_rc = (RAMDISK / "init.recovery.mt6765.rc").read_text(encoding="utf-8")
    if "setprop sys.usb.configfs 1" not in mt_rc:
        fail("MT6765 recovery rc must enable configfs USB mode")

    required_payload = (
        "system/bin/keystore2",
        "system/bin/hw/android.hardware.gatekeeper@1.0-service",
        "system/bin/hw/android.hardware.keymaster@4.1-service",
        "system/etc/init/android.hardware.gatekeeper@1.0-service.rc",
        "system/etc/init/android.hardware.keymaster@4.1-service.rc",
        "system/etc/vintf/manifest/android.hardware.keymaster@4.1-service.xml",
        "system/lib64/libkeymaster4.so",
        "system/lib64/libkeymaster41.so",
        "system/lib64/libkeymaster4support.so",
        "system/lib64/libkeymaster4_1support.so",
        "system/lib64/libkeymaster_messages.so",
        "system/lib64/libkeymaster_portable.so",
        "system/lib64/libpuresoftkeymasterdevice.so",
        "system/lib64/libcppbor_external.so",
        "system/lib64/stock/android.hardware.security.keymint-V4-ndk.so",
        "system/lib64/stock/android.hardware.confirmationui-V1-ndk.so",
        "system/lib64/stock/android.hardware.security.secureclock-V1-ndk.so",
        "system/lib64/stock/android.hardware.security.sharedsecret-V1-ndk.so",
        "system/lib64/stock/android.security.compat-ndk.so",
        "system/lib64/stock/libkeystore2_aaid.so",
        "system/lib64/stock/libkeystore2_apc_compat.so",
        "system/lib64/stock/libkeystore2_crypto.so",
        "system/lib64/stock/libkm_compat_service.so",
        "system/lib64/stock/libc++.so",
        "system/lib64/stock/libhidlbase.so",
        "system/lib64/stock/libbinder_ndk.so",
        "system/lib64/stock/libbinder.so",
        "system/lib64/stock/libapexsupport.so",
    )
    for relative in required_payload:
        require(RAMDISK / relative)

    for line in (
        "mount ext4 /dev/block/by-name/vendor /vendor ro",
        "start vendor.keymaster-4-1",
        "start vendor.gatekeeper-1-0",
    ):
        if line not in mt_rc:
            fail(f"recovery HAL startup missing: {line}")

    print("A25 recovery layout checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
