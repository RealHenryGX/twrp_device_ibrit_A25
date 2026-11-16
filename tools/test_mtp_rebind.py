#!/usr/bin/env python3
"""Run the recovery MTP rebind helper against a mocked Android init/configfs."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "recovery/root/sbin/mtp_rebind.sh"
TEST_ROOT = ROOT.parent / "local-verify"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def run_case(
    name: str,
    *,
    mtp_ready: bool,
    adb_ready: bool,
    fail_mtp_link: bool = False,
    no_adb_after_fallback: bool = False,
) -> None:
    case = Path(tempfile.mkdtemp(prefix=f"mtp-state-{name}-", dir=TEST_ROOT))
    try:
        bin_dir = case / "bin"
        bin_dir.mkdir()
        gadget = case / "config/usb_gadget/g1"
        for relative in (
            "configs/b.1/strings/0x409",
            "functions/ffs.adb",
            "functions/ffs.mtp",
        ):
            (gadget / relative).mkdir(parents=True, exist_ok=True)
        (gadget / "UDC").write_text("", encoding="ascii")
        (gadget / "idVendor").write_text("", encoding="ascii")
        (gadget / "idProduct").write_text("", encoding="ascii")
        mtp_ep1 = case / "dev/mtp/ep1"
        adb_ep1 = case / "dev/adb/ep1"
        mtp_ep1.parent.mkdir(parents=True)
        adb_ep1.parent.mkdir(parents=True)
        if mtp_ready:
            mtp_ep1.touch()
        if adb_ready:
            adb_ep1.touch()

        prop_file = case / "properties"
        status_file = case / "mtp.status"
        prop_file.write_text(
            "sys.usb.controller=musb-hdrc\n"
            "sys.usb.config=mtp,adb\n"
            f"sys.usb.state={'mtp,adb' if mtp_ready and adb_ready else 'none'}\n"
            f"sys.usb.ffs.ready={1 if adb_ready else 0}\n"
            "sys.usb.ffs.mtp.ready=0\n",
            encoding="ascii",
        )

        write_executable(
            bin_dir / "getprop",
            "#!/bin/sh\n"
            "awk -F= -v key=\"$1\" '$1 == key {sub(/^[^=]*=/, \"\"); print; found=1} END {if (!found) exit 0}' \"$A25_TEST_PROPS\"\n",
        )
        write_executable(
            bin_dir / "setprop",
            "#!/bin/sh\n"
            "key=$1; shift; value=$*; tmp=\"$A25_TEST_PROPS.tmp\"\n"
            "awk -F= -v key=\"$key\" '$1 != key' \"$A25_TEST_PROPS\" > \"$tmp\"\n"
            "printf '%s=%s\\n' \"$key\" \"$value\" >> \"$tmp\"; mv \"$tmp\" \"$A25_TEST_PROPS\"\n"
            "case \"$key:$value\" in\n"
            "  sys.usb.config:none)\n"
            "    \"$0\" sys.usb.ffs.ready 0; \"$0\" sys.usb.state none\n"
            "    rm -f \"$A25_TEST_GADGET/configs/b.1/f1\" \"$A25_TEST_GADGET/configs/b.1/f2\";;\n"
            "  sys.usb.config:adb)\n"
            "    if [ \"$(\"$A25_TEST_BIN/getprop\" sys.usb.ffs.ready)\" != 1 ]; then\n"
            "      \"$A25_TEST_BIN/start\" adbd\n"
            "    fi\n"
            "    if [ \"$(\"$A25_TEST_BIN/getprop\" sys.usb.ffs.ready)\" = 1 ]; then\n"
            "      ln -s \"$A25_TEST_GADGET/functions/ffs.adb\" \"$A25_TEST_GADGET/configs/b.1/f1\" 2>/dev/null || :\n"
            "      printf '%s\\n' \"$(\"$A25_TEST_BIN/getprop\" sys.usb.controller)\" > \"$A25_TEST_GADGET/UDC\"\n"
            "      \"$0\" sys.usb.state adb\n"
            "    fi;;\n"
            "esac\n",
        )
        write_executable(
            bin_dir / "start",
            "#!/bin/sh\n"
            "[ \"$1\" = adbd ] || exit 0\n"
            "if [ \"${A25_TEST_NO_ADB:-0}\" = 0 ]; then touch \"$A25_TEST_ADB_EP1\"; \"$A25_TEST_BIN/setprop\" sys.usb.ffs.ready 1; fi\n",
        )
        write_executable(bin_dir / "sleep", "#!/bin/sh\nexit 0\n")
        write_executable(
            bin_dir / "ln",
            "#!/bin/sh\n"
            "case \"$2\" in *ffs.mtp) [ \"${A25_TEST_FAIL_MTP_LINK:-0}\" = 1 ] && exit 1;; esac\n"
            "exec /bin/ln \"$@\"\n",
        )

        env = os.environ.copy()
        env.update(
            PATH=f"{bin_dir}:/usr/bin:/bin",
            A25_TEST_BIN=str(bin_dir),
            A25_TEST_PROPS=str(prop_file),
            A25_TEST_GADGET=str(gadget),
            A25_TEST_ADB_EP1=str(adb_ep1),
            A25_TEST_FAIL_MTP_LINK="1" if fail_mtp_link else "0",
            A25_TEST_NO_ADB="1" if no_adb_after_fallback else "0",
            A25_MTP_GADGET_ROOT=str(gadget),
            A25_MTP_EP1=str(mtp_ep1),
            A25_ADB_EP1=str(adb_ep1),
            A25_MTP_STATUS_FILE=str(status_file),
        )
        result = subprocess.run(["bash", str(HELPER)], env=env, text=True, capture_output=True, check=False)
        props = dict(line.split("=", 1) for line in prop_file.read_text(encoding="ascii").splitlines())

        if name == "success":
            assert result.returncode == 0, result.stderr
            assert status_file.read_text(encoding="ascii").strip() == "active"
            assert props["sys.usb.ffs.mtp.ready"] == "1", props
            assert props["sys.usb.state"] == "mtp,adb", props
            assert (gadget / "configs/b.1/f1").is_symlink()
            assert (gadget / "configs/b.1/f2").is_symlink()
            assert (gadget / "UDC").read_text(encoding="ascii").strip() == "musb-hdrc"
        elif no_adb_after_fallback:
            assert result.returncode == 1, (result.returncode, result.stderr)
            assert status_file.read_text(encoding="ascii").strip() == "fallback-adb-not-ready"
            assert props["sys.usb.config"] == "adb", props
        else:
            assert result.returncode == 1, (result.returncode, result.stderr)
            assert props["sys.usb.config"] == "adb", props
            assert props["sys.usb.state"] == "adb", props
            assert status_file.read_text(encoding="ascii").strip() == "fallback-adb-restored"
            assert (gadget / "configs/b.1/f1").is_symlink()
            assert not (gadget / "configs/b.1/f2").exists()
            assert (gadget / "UDC").read_text(encoding="ascii").strip() == "musb-hdrc"
    finally:
        shutil.rmtree(case)


def main() -> None:
    TEST_ROOT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["sh", "-n", str(HELPER)], check=True)
    run_case("success", mtp_ready=True, adb_ready=True)
    run_case("mtp-timeout", mtp_ready=False, adb_ready=False)
    run_case("adb-timeout", mtp_ready=True, adb_ready=False)
    run_case("configfs-bind-failure", mtp_ready=True, adb_ready=True, fail_mtp_link=True)
    run_case("adb-unavailable", mtp_ready=False, adb_ready=False, no_adb_after_fallback=True)
    print("MTP rebind state-machine checks passed: success, endpoint timeouts, bind failure, adb unavailable")


if __name__ == "__main__":
    main()
