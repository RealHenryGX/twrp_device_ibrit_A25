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

    required_usb = (
        "mount configfs none /config",
        "mount functionfs adb /dev/usb-ffs/adb",
        "setprop sys.usb.config adb",
        "write /config/usb_gadget/g1/UDC ${sys.usb.controller}",
        "on property:init.svc.adbd=stopped && property:sys.usb.config=adb",
    )
    for line in required_usb:
        if line not in usb_rc:
            fail(f"USB recovery rc missing: {line}")

    required_payload = (
        "system/bin/hw/android.hardware.gatekeeper@1.0-service",
        "system/bin/hw/android.hardware.keymaster@4.1-service",
        "system/etc/init/android.hardware.gatekeeper@1.0-service.rc",
        "system/etc/init/android.hardware.keymaster@4.1-service.rc",
        "system/lib64/libkeymaster4.so",
        "system/lib64/libkeymaster41.so",
        "system/lib64/libkeymaster4support.so",
        "system/lib64/libkeymaster4_1support.so",
        "system/lib64/libkeymaster_messages.so",
        "system/lib64/libkeymaster_portable.so",
        "system/lib64/libpuresoftkeymasterdevice.so",
        "system/lib64/libcppbor_external.so",
    )
    for relative in required_payload:
        require(RAMDISK / relative)

    print("A25 recovery layout checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
