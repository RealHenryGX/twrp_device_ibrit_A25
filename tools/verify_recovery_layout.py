#!/usr/bin/env python3
"""Static checks for the A25 recovery ramdisk.

These checks intentionally validate only facts that are required before a
device flash/test cycle: the MTK USB gadget ownership, the metadata block
alias used by FBE, and the runtime-mounted stock crypto services.
"""

from pathlib import Path
import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ramdisk-root",
        type=Path,
        help="built recovery/root directory to validate; defaults to the DT source tree",
    )
    args = parser.parse_args()

    fstab = (ROOT / "recovery.fstab").read_text(encoding="utf-8")
    ramdisk = args.ramdisk_root.resolve() if args.ramdisk_root else RAMDISK
    usb_rc = (ramdisk / "init.recovery.usb.rc").read_text(encoding="utf-8")

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
    require(ramdisk / "init.recovery.mt6765.rc")
    mt_rc = (ramdisk / "init.recovery.mt6765.rc").read_text(encoding="utf-8")
    product_mk = (ROOT / "twrp_A25.mk").read_text(encoding="utf-8")
    if "setprop sys.usb.configfs 1" not in mt_rc:
        fail("MT6765 recovery rc must enable configfs USB mode")

    required_payload = (
        "system/etc/init/android.hardware.gatekeeper@1.0-service.rc",
        "system/etc/init/android.hardware.keymaster@4.1-service.rc",
        "system/etc/vintf/manifest/android.hardware.keymaster@4.1-service.xml",
    )
    for relative in required_payload:
        require(ramdisk / relative)

    if args.ramdisk_root:
        require(ramdisk / "etc/recovery.fstab")

    for line in (
        "mount ext4 /dev/block/by-name/system /system_real ro",
        "mount ext4 /dev/block/by-name/vendor /vendor ro",
        "start vendor.keymaster-4-1",
        "start vendor.gatekeeper-1-0",
        "service vendor.keymaster-4-1 /vendor/bin/hw/android.hardware.keymaster@4.1-service",
        "service vendor.gatekeeper-1-0 /vendor/bin/hw/android.hardware.gatekeeper@1.0-service",
        "service keystore2 /system_real/bin/keystore2",
    ):
        if line not in mt_rc:
            fail(f"recovery HAL startup missing: {line}")

    if "device/ibrit/A25/recovery.fstab:recovery/root/system/etc/recovery.fstab" not in product_mk:
        fail("recovery.fstab is not copied to system/etc/recovery.fstab")

    forbidden_payload = (
        "system/bin/keystore2",
        "system/bin/hw/android.hardware.gatekeeper@1.0-service",
        "system/bin/hw/android.hardware.keymaster@4.1-service",
        "system/lib64/stock",
    )
    for relative in forbidden_payload:
        if (ramdisk / relative).exists():
            fail(f"stock crypto payload must come from mounted partitions: {relative}")

    print("A25 recovery layout checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
