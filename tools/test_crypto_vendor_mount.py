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
        mounts = case / "mounts"
        if already_mounted:
            mounts.write_text(f"{target} /vendor ext4 ro 0 0\n", encoding="utf-8")
        else:
            mounts.write_text("", encoding="utf-8")
        props = case / "props"
        props.write_text(f"orangefox.a25_vendor.ready={1 if already_mounted else 0}\n", encoding="ascii")
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
            "printf '%s=%s\\n' \"$1\" \"$2\" >> \"$tmp\"; mv \"$tmp\" \"$A25_TEST_PROPS\"\n",
        )
        executable(
            bin_dir / "mount",
            "#!/bin/sh\n"
            "[ \"$1 $2 $3 $4\" = '-t ext4 -o ro' ] || exit 2\n"
            "printf '%s %s ext4 ro 0 0\\n' \"$5\" \"$6\" >> \"$A25_TEST_MOUNTS\"\n"
            "printf '%s %s %s %s %s %s\\n' \"$@\" >> \"$A25_TEST_MOUNT_LOG\"\n",
        )
        executable(
            bin_dir / "sleep",
            "#!/bin/sh\n"
            "[ \"$1\" = 0.2 ] || exit 3\n"
            "if [ ! -e \"$A25_TEST_BLOCK_LINK\" ]; then ln -s \"$A25_TEST_BLOCK_TARGET\" \"$A25_TEST_BLOCK_LINK\"; fi\n",
        )
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
            A25_PROC_MOUNTS=str(mounts),
        )
        result = subprocess.run(["bash", str(HELPER)], env=env, text=True, capture_output=True, check=False)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        final_props = dict(line.split("=", 1) for line in props.read_text(encoding="ascii").splitlines())
        assert final_props["orangefox.a25_vendor.ready"] == "1", final_props
        if already_mounted:
            assert not mount_log.exists(), "idempotent invocation unexpectedly remounted vendor"
        else:
            assert mount_log.read_text(encoding="utf-8").strip() == f"-t ext4 -o ro {target} /vendor"
            assert mounts.read_text(encoding="utf-8").strip() == f"{target} /vendor ext4 ro 0 0"
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
