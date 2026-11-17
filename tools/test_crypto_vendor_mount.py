#!/usr/bin/env python3
"""Exercise the early, idempotent vendor mount helper with mocked init state."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "recovery/root/sbin/a25_mount_crypto_vendor.sh"
TEST_ROOT = ROOT.parent / "local-verify"
EXPECTED_DATA_FSTAB = (
    "/dev/block/by-name/userdata /data ext4 noatime,nosuid,nodev,noauto_da_alloc,errors=panic,inlinecrypt "
    "latemount,wait,check,quota,reservedsize=128M,formattable,checkpoint=block,"
    "fileencryption=aes-256-xts:aes-256-cts:v2,keydirectory=/metadata/vold/metadata_encryption,"
    "metadata_encryption=aes-256-xts"
)


def executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def run_case(name: str, *, already_mounted: bool) -> None:
    case = Path(tempfile.mkdtemp(prefix=f"crypto-vendor-{name}-", dir=TEST_ROOT))
    try:
        bin_dir = case / "bin"
        bin_dir.mkdir()
        device_dir = case / "dev/block"
        device_dir.mkdir(parents=True)
        target = device_dir / "dm-0"
        target.touch()
        block_link = device_dir / "mapper/vendor"
        block_link.parent.mkdir(parents=True)
        if already_mounted:
            block_link.symlink_to(target)
        system_target = device_dir / "dm-1"
        system_target.touch()
        system_link = device_dir / "mapper/system"
        system_link.symlink_to(system_target)
        system_build_prop = case / "system-build.prop"
        system_build_prop.write_text(
            "ro.build.version.release=16\n"
            "ro.build.version.sdk=36\n"
            "ro.build.version.security_patch=2025-12-01\n",
            encoding="ascii",
        )
        additional_fstab = case / "additional.fstab"
        additional_fstab.write_text(
            "/dev/block/by-name/userdata /data ext4 noatime,fileencryption=aes-256-xts:aes-256-cts:v2,keydirectory=/metadata/vold/metadata_encryption\n"
            "/dev/block/by-name/cache /cache ext4 defaults\n",
            encoding="utf-8",
        )
        staged_fstab = case / "a25-additional.fstab"
        staged_fstab.touch()
        ctl_log = case / "ctl-start.log"
        resetprop_log = case / "resetprop.log"
        mounts = case / "mounts"
        if already_mounted:
            mounts.write_text(f"{target} /vendor ext4 ro 0 0\n{system_target} /system_root ext4 ro 0 0\n", encoding="utf-8")
        else:
            mounts.write_text(f"{system_target} /system_root ext4 ro 0 0\n", encoding="utf-8")
        props = case / "props"
        props.write_text(
            f"orangefox.a25_vendor.ready={1 if already_mounted else 0}\n"
            "init.svc.servicemanager=running\n",
            encoding="ascii",
        )
        mount_log = case / "mount.log"

        executable(
            bin_dir / "getprop",
            "#!/bin/sh\n"
            "awk -F= -v key=\"$1\" '$1 == key {sub(/^[^=]*=/, \"\"); print; found=1} END {if (!found) exit 0}' \"$A25_TEST_PROPS\"\n",
        )
        executable(
            bin_dir / "setprop",
            "#!/bin/sh\n"
            "tmp=\"$A25_TEST_PROPS.tmp\"; awk -F= -v key=\"$1\" '$1 != key' \"$A25_TEST_PROPS\" > \"$tmp\"\n"
            "printf '%s=%s\\n' \"$1\" \"$2\" >> \"$tmp\"; mv \"$tmp\" \"$A25_TEST_PROPS\"\n"
            "if [ \"$1\" = ctl.start ]; then printf '%s\\n' \"$2\" >> \"$A25_TEST_CTL\"; printf 'start %s\\n' \"$2\" >> \"$A25_TEST_SEQUENCE\"; fi\n",
        )
        executable(
            bin_dir / "resetprop",
            "#!/bin/sh\n"
            "[ \"$1\" = -n ] || exit 3\n"
            "printf '%s=%s\\n' \"$2\" \"$3\" >> \"$A25_TEST_RESETPROP\"\n"
            "printf 'reset %s=%s\\n' \"$2\" \"$3\" >> \"$A25_TEST_SEQUENCE\"\n",
        )
        executable(
            bin_dir / "mount",
            "#!/bin/sh\n"
            "if [ \"$1 $2\" = '-o bind' ]; then\n"
            "  cp \"$3\" \"$4\" || exit 2\n"
            "  printf 'tmpfs %s tmpfs rw 0 0\\n' \"$4\" >> \"$A25_TEST_MOUNTS\"\n"
            "  printf '%s\\n' \"$*\" >> \"$A25_TEST_MOUNT_LOG\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1 $2 $3 $4\" = '-t ext4 -o ro' ]; then\n"
            "  printf '%s %s ext4 ro 0 0\\n' \"$5\" \"$6\" >> \"$A25_TEST_MOUNTS\"\n"
            "else exit 2; fi\n"
            "printf '%s\\n' \"$*\" >> \"$A25_TEST_MOUNT_LOG\"\n",
        )
        executable(
            bin_dir / "sleep",
            "#!/bin/sh\n"
            "[ \"$1\" = 0.2 ] || exit 3\n"
            "if [ ! -e \"$A25_TEST_BLOCK_LINK\" ]; then ln -s \"$A25_TEST_BLOCK_TARGET\" \"$A25_TEST_BLOCK_LINK\"; fi\n",
        )
        executable(bin_dir / "chown", "#!/bin/sh\n[ \"$1\" = 1017:1017 ] && [ -d \"$2\" ]\n")
        env = os.environ.copy()
        env.update(
            PATH=f"{bin_dir}:/usr/bin:/bin",
            A25_TEST_PROPS=str(props),
            A25_TEST_MOUNTS=str(mounts),
            A25_TEST_MOUNT_LOG=str(mount_log),
            A25_TEST_BLOCK_LINK=str(block_link),
            A25_TEST_BLOCK_TARGET=str(target),
            A25_VENDOR_BLOCK=str(block_link),
            A25_VENDOR_MOUNT="/vendor",
            A25_SYSTEM_BLOCK=str(system_link),
            A25_SYSTEM_MOUNT="/system_root",
            A25_ADDITIONAL_FSTAB=str(additional_fstab),
            A25_STAGED_ADDITIONAL_FSTAB=str(staged_fstab),
            A25_CRYPTO_VENDOR_STATUS_FILE=str(case / "status"),
            A25_TEST_CTL=str(ctl_log),
            A25_TEST_RESETPROP=str(resetprop_log),
            A25_TEST_SEQUENCE=str(case / "crypto-start-sequence.log"),
            A25_PROC_MOUNTS=str(mounts),
            A25_SYSTEM_BUILD_PROP=str(system_build_prop),
            TMPDIR=str(case / "missing-tmp"),
        )
        result = subprocess.run(["bash", str(HELPER)], env=env, text=True, capture_output=True, check=False)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        first_mount_log = mount_log.read_text(encoding="utf-8").splitlines()
        second = subprocess.run(["bash", str(HELPER)], env=env, text=True, capture_output=True, check=False)
        assert second.returncode == 0, (second.returncode, second.stdout, second.stderr)
        final_props = dict(line.split("=", 1) for line in props.read_text(encoding="ascii").splitlines())
        assert final_props["orangefox.a25_vendor.ready"] == "1", final_props
        assert final_props["orangefox.a25_system.ready"] == "1", final_props
        expected_crypto_starts = [
            "vendor.keymaster-4-1",
            "vendor.gatekeeper-1-0",
        ]
        assert ctl_log.read_text(encoding="ascii").splitlines() == expected_crypto_starts * 2
        expected_prop_sync = [
            "ro.build.version.release=16",
            "ro.build.version.sdk=36",
            "ro.build.version.security_patch=2025-12-01",
        ]
        assert resetprop_log.read_text(encoding="ascii").splitlines() == expected_prop_sync * 2
        expected_sequence = [
            "reset ro.build.version.release=16",
            "reset ro.build.version.sdk=36",
            "reset ro.build.version.security_patch=2025-12-01",
            "start vendor.keymaster-4-1",
            "start vendor.gatekeeper-1-0",
        ]
        assert (case / "crypto-start-sequence.log").read_text(encoding="ascii").splitlines() == expected_sequence * 2
        assert additional_fstab.read_text(encoding="utf-8").splitlines() == [EXPECTED_DATA_FSTAB]
        assert "additional-fstab-corrected" in (case / "status").read_text(encoding="utf-8")
        expected_mounts = [f"-o bind {staged_fstab} {additional_fstab}"]
        if not already_mounted:
            expected_mounts.insert(0, f"-t ext4 -o ro {target} /vendor")
        assert first_mount_log == expected_mounts
        assert mount_log.read_text(encoding="utf-8").splitlines() == expected_mounts, "repeat invocation added a duplicate fstab mount"
        assert f"tmpfs {additional_fstab} tmpfs rw 0 0" in mounts.read_text(encoding="utf-8")
        if not already_mounted:
            assert f"{target} /vendor ext4 ro 0 0" in mounts.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(case)


def main() -> None:
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sh", "-n", str(HELPER)], check=True)
    run_case("already-ready", already_mounted=True)
    run_case("mapper-arrives-after-start", already_mounted=False)
    print("Crypto vendor mount checks passed: idempotent ready state and delayed mapper availability")


if __name__ == "__main__":
    main()
