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
        try:
            display = path.relative_to(ROOT)
        except ValueError:
            display = path
        fail(f"missing or empty: {display}")


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
    require(ramdisk / "init.recovery.usb.rc")
    usb_rc = (ramdisk / "init.recovery.usb.rc").read_text(encoding="utf-8")

    if "import /init.recovery.mt6765.rc" not in usb_rc:
        fail("USB compatibility rc must explicitly import the MT6765 DT rc")

    metadata = re.search(r"^/metadata\s+\S+\s+([^\s]+)", fstab, re.MULTILINE)
    if not metadata or not metadata.group(1).endswith("/md_udc"):
        fail("/metadata must use /dev/block/by-name/md_udc")

    # OrangeFox 12.1 owns the ADB/fastboot configfs state machine. The DT rc
    # may extend only MTP after FunctionFS publishes descriptors.
    if any(token in usb_rc for token in (
        "mount configfs none /config",
        "mount functionfs adb /dev/usb-ffs/adb",
        "setprop sys.usb.config adb",
    )):
        fail("device-tree USB rc must leave configfs and ADB ownership to OrangeFox")
    require(ramdisk / "init.recovery.mt6765.rc")
    mt_rc = (ramdisk / "init.recovery.mt6765.rc").read_text(encoding="utf-8")
    if "setprop sys.usb.configfs 1" not in mt_rc:
        fail("MT6765 recovery rc must enable configfs USB mode")
    for token in (
        "mkdir /config/usb_gadget/g1/functions/ffs.mtp",
        "mount functionfs mtp /dev/usb-ffs/mtp",
        "on property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1",
        "on property:sys.usb.ffs.mtp.ready=1 && property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1",
        "symlink /config/usb_gadget/g1/functions/ffs.adb /config/usb_gadget/g1/configs/b.1/f1",
        "symlink /config/usb_gadget/g1/functions/ffs.mtp /config/usb_gadget/g1/configs/b.1/f2",
    ):
        if token not in mt_rc:
            fail(f"MT6765 configfs MTP support missing: {token}")

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
        "on property:orangefox.mount_to_decrypt=1",
        "start vendor.keymaster-4-1",
        "start vendor.gatekeeper-1-0",
        "service vendor.keymaster-4-1 /vendor/bin/hw/android.hardware.keymaster@4.1-service",
        "service vendor.gatekeeper-1-0 /vendor/bin/hw/android.hardware.gatekeeper@1.0-service",
        "service keystore2 /system_root/system/bin/keystore2",
    ):
        if line not in mt_rc:
            fail(f"recovery HAL startup missing: {line}")

    board_config = (ROOT / "BoardConfig.mk").read_text(encoding="utf-8")
    if "TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab" not in board_config:
        fail("BoardConfig must use TARGET_RECOVERY_FSTAB for first-stage /etc/recovery.fstab")
    if "TW_EXCLUDE_MTP := true" in board_config:
        fail("MTP must be included for FunctionFS MTP validation")

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
