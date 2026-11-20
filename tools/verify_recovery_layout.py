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
import xml.etree.ElementTree as ET


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

    ramdisk = args.ramdisk_root.resolve() if args.ramdisk_root else RAMDISK
    fstab_path = ramdisk / "fstab.mt6765" if args.ramdisk_root else ROOT / "recovery/root/fstab.mt6765"
    require(fstab_path)
    fstab = fstab_path.read_text(encoding="utf-8")
    gui_xml = ramdisk / "twres/ui.xml" if args.ramdisk_root else ROOT / "recovery/theme-a25-480x800.xml"
    require(gui_xml)
    try:
        gui_root = ET.parse(gui_xml).getroot()
    except ET.ParseError as exc:
        fail(f"A25 Recovery GUI XML is invalid: {exc}")
    resolution = gui_root.find("./details/resolution")
    if resolution is None or resolution.attrib != {"width": "480", "height": "800"}:
        fail("A25 Recovery GUI must use the verified 480x800 layout")
    if args.ramdisk_root:
        stock_theme_xml = ROOT.parents[2] / "bootable/recovery/gui/theme/portrait_hdpi/ui.xml"
        require(stock_theme_xml)
        stock_theme_root = ET.parse(stock_theme_xml).getroot()
        custom_images = {node.attrib.get("name") for node in gui_root.findall("./resources/image")}
        stock_images = {node.attrib.get("name") for node in stock_theme_root.findall("./resources/image")}
        if custom_images != stock_images:
            fail("A25 custom UI image resources must match the available portrait_hdpi asset set")
    if not args.ramdisk_root:
        board_config = (ROOT / "BoardConfig.mk").read_text(encoding="utf-8")
        if "TW_THEME := portrait_hdpi" not in board_config or "TW_CUSTOM_THEME := device/ibrit/A25/recovery/theme-a25-480x800.xml" not in board_config:
            fail("A25 must load its 480x800 custom UI over the available portrait_hdpi image resources")
    require(ramdisk / "init.recovery.usb.rc")
    usb_rc = (ramdisk / "init.recovery.usb.rc").read_text(encoding="utf-8")

    if "import /init.recovery.mt6765.rc" not in usb_rc:
        fail("USB compatibility rc must explicitly import the MT6765 DT rc")

    fstab_entries = [line.split() for line in fstab.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    metadata = next((entry for entry in fstab_entries if len(entry) >= 3 and entry[1] == "/metadata"), None)
    if not metadata or not metadata[0].endswith("/md_udc"):
        fail("/metadata must use /dev/block/by-name/md_udc")
    data = next((entry for entry in fstab_entries if len(entry) >= 5 and entry[1] == "/data"), None)
    if not data or data[0] != "/dev/block/by-name/userdata" or data[2] != "ext4":
        fail("Android recovery fstab must map ext4 /data to the physical userdata partition")
    for token in ("inlinecrypt", "fileencryption=aes-256-xts:aes-256-cts:v2", "keydirectory=/metadata/vold/metadata_encryption"):
        if token not in " ".join(data[3:5]):
            fail(f"Android recovery fstab /data entry is missing {token}")
    if not any(len(entry) >= 5 and entry[1] == "/system_root" and "first_stage_mount" in entry[4] for entry in fstab_entries):
        fail("Android recovery fstab must describe first-stage logical /system_root")

    twrp_fstab_path = ramdisk / "system/etc/recovery.fstab" if args.ramdisk_root else ROOT / "recovery.fstab"
    require(twrp_fstab_path)
    twrp_fstab = twrp_fstab_path.read_text(encoding="utf-8")
    twrp_entries = [line.split() for line in twrp_fstab.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if any(len(entry) >= 3 and entry[1] == "/data" for entry in twrp_entries):
        fail("OrangeFox fstab must use TWRP field order: mount point, filesystem, block device")
    twrp_data = next((entry for entry in twrp_entries if entry[0] == "/data"), None)
    if not twrp_data or twrp_data[1:3] != ["ext4", "/dev/block/by-name/userdata"]:
        fail("OrangeFox fstab must map /data to the physical ext4 userdata partition")
    for token in (
        "fileencryption=aes-256-xts:aes-256-cts:v2",
        "keydirectory=/metadata/vold/metadata_encryption",
        "metadata_encryption=aes-256-xts",
    ):
        if token not in " ".join(twrp_data[3:]):
            fail(f"OrangeFox /data fstab is missing {token}")

    additional_fstab = ramdisk / "system/etc/additional.fstab"
    require(additional_fstab)
    additional_entries = [
        line.split()
        for line in additional_fstab.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if len(additional_entries) != 1 or additional_entries[0][:3] != [
        "/dev/block/by-name/userdata", "/data", "ext4"
    ]:
        fail("packaged fs_mgr additional.fstab must contain exactly the A25 userdata entry")
    for token in (
        "fileencryption=aes-256-xts:aes-256-cts:v2",
        "keydirectory=/metadata/vold/metadata_encryption",
        "metadata_encryption=aes-256-xts",
    ):
        if token not in " ".join(additional_entries[0][3:]):
            fail(f"packaged additional.fstab /data entry is missing {token}")
    twrp_vendor = next((entry for entry in twrp_entries if entry[0] == "/vendor"), None)
    if not twrp_vendor or "fsflags=ro" not in " ".join(twrp_vendor[3:]):
        fail("OrangeFox must mount logical /vendor read-only")

    # OrangeFox 12.1 owns the ADB/fastboot configfs state machine. The DT rc
    # may extend only MTP after FunctionFS publishes descriptors.
    if any(token in usb_rc for token in (
        "mount configfs none /config",
        "mount functionfs adb /dev/usb-ffs/adb",
        "setprop sys.usb.config adb",
    )):
        fail("device-tree USB compatibility rc must leave base configfs ADB ownership to system init")
    require(ramdisk / "init.recovery.mt6765.rc")
    mt_rc = (ramdisk / "init.recovery.mt6765.rc").read_text(encoding="utf-8")
    if "setprop sys.usb.configfs 1" not in mt_rc:
        fail("MT6765 recovery rc must enable configfs USB mode")
    # Android init owns base ADB configfs transitions. The DT adds MTP once
    # both ADB and MTP FunctionFS endpoints are ready.
    for token in (
        "mkdir /config/usb_gadget/g1/functions/ffs.mtp",
        "mount functionfs mtp /dev/usb-ffs/mtp",
        "on property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1",
        "start adbd",
        "start mtp_rebind",
        "service mtp_rebind /sbin/sh /sbin/mtp_rebind.sh",
        "property:sys.usb.ffs.ready=1 && property:sys.usb.ffs.mtp.ready=1",
        "symlink /config/usb_gadget/g1/functions/ffs.mtp",
        "write /config/usb_gadget/g1/UDC ${sys.usb.controller}",
    ):
        if token not in mt_rc:
            fail(f"MT6765 MTP FunctionFS support missing: {token}")
    mtp_action = mt_rc.split("on property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1", 1)[1]
    if mtp_action.index("start adbd") > mtp_action.index("start mtp_rebind"):
        fail("MTP transition must start adbd before the rebind helper")
    if mtp_action.index("write /config/usb_gadget/g1/UDC ${sys.usb.controller}") > mtp_action.index("setprop sys.usb.state ${sys.usb.config}"):
        fail("MTP state must be published only after the gadget is bound")
    require(ramdisk / "sbin/mtp_rebind.sh")
    rebind_text = (ramdisk / "sbin/mtp_rebind.sh").read_text(encoding="utf-8")
    for token in (
        "/dev/usb-ffs/mtp/ep1",
        "/dev/usb-ffs/adb/ep1",
        "fallback_adb()",
        "setprop sys.usb.config adb",
        'setprop sys.usb.ffs.mtp.ready 1',
        "fallback_adb init-mtp-bind-timeout",
        'write_status "fallback-adb-restored:$reason"',
        "STATUS_FILE=${A25_MTP_STATUS_FILE:-/tmp/mtp_rebind.status}",
    ):
        if token not in rebind_text:
            fail(f"MTP deferred binding script missing: {token}")
    if "start adbd" in rebind_text:
        fail("rebind shell must request adb through sys.usb.config, not init rc syntax")
    required_payload = (
        "system/etc/init/android.hardware.gatekeeper@1.0-service.rc",
        "system/etc/init/android.hardware.keymaster@4.1-service.rc",
        "system/etc/init/keystore2.rc",
        "system/etc/vintf/manifest.xml",
        "system/etc/vintf/manifest/android.system.keystore2-service.xml",
    )
    for relative in required_payload:
        if relative in (
            "system/etc/init/keystore2.rc",
            "system/etc/vintf/manifest/android.system.keystore2-service.xml",
        ) and not args.ramdisk_root:
            continue
        require(ramdisk / relative)
    keyring_source = ROOT / "recovery/a25_fscrypt_keyring.c"
    require(keyring_source)
    keyring_source_text = keyring_source.read_text(encoding="utf-8")
    for token in (
        "syscall(__NR_add_key",
        '"keyring", "fscrypt"',
        "KEY_SPEC_SESSION_KEYRING",
    ):
        if token not in keyring_source_text:
            fail(f"A25 fscrypt keyring helper missing: {token}")
    init_action = mt_rc.split("on init", 1)[1].split("\non ", 1)[0]
    if "start a25_fscrypt_keyring" not in init_action:
        fail("A25 fscrypt session keyring must be created during init before recovery crypto setup")
    keyring_service = "service a25_fscrypt_keyring /system/bin/a25_fscrypt_keyring"
    if keyring_service not in mt_rc:
        fail("A25 fscrypt keyring init service is missing")
    if args.ramdisk_root:
        require(ramdisk / "system/bin/a25_fscrypt_keyring")
    else:
        product_mk = (ROOT / "twrp_A25.mk").read_text(encoding="utf-8")
        android_bp = (ROOT / "Android.bp").read_text(encoding="utf-8")
        if "a25_fscrypt_keyring" not in product_mk or "name: \"a25_fscrypt_keyring\"" not in android_bp:
            fail("A25 fscrypt keyring helper must be built into the recovery ramdisk")
    logd_rc = mt_rc
    for token in (
        "service a25_logd /system_root/system/bin/logd",
        "socket logd stream",
        "socket logdr seqpacket",
        "socket logdw dgram+passcred",
    ):
        if token not in logd_rc:
            fail(f"recovery logd service missing: {token}")
    if args.ramdisk_root:
        keystore_rc = (ramdisk / "system/etc/init/keystore2.rc").read_text(encoding="utf-8")
    else:
        keystore_patch = ROOT / "patches/a25-keystore2-rc.patch"
        require(keystore_patch)
        patch_text = keystore_patch.read_text(encoding="utf-8")
        keystore_rc = "\n".join(
            line[1:] for line in patch_text.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
    for token in (
        "service keystore2 /system/bin/keystore2 /tmp/a25-keystore2-db",
        "interface aidl android.system.keystore2.IKeystoreService/default",
        "user keystore",
        "group keystore",
        "setenv LD_LIBRARY_PATH /system/lib64:/system/lib64/vndk-sp:",
        "stdio_to_kmsg",
        "seclabel u:r:recovery:s0",
    ):
        if token not in keystore_rc:
            fail(f"recovery Keystore2 AIDL service missing: {token}")
    if args.ramdisk_root:
        require(ramdisk / "system/bin/keystore2")
    framework_manifest = (ramdisk / "system/etc/vintf/manifest.xml").read_text(encoding="utf-8")
    if '<manifest version="4.0" type="framework">' not in framework_manifest:
        fail("Recovery framework VINTF root must match its libvintf 4.0 parser")
    if (ramdisk / "system/etc/vintf/manifest/android.hardware.keymaster@4.1-service.xml").exists():
        fail("device Keymaster HAL must remain in vendor VINTF, not framework fragments")

    android_fstab = ramdisk / "fstab.mt6765"
    first_stage_fstab = ramdisk / "first_stage_ramdisk" / "fstab.mt6765"
    require(android_fstab)
    require(first_stage_fstab)
    runtime_fstab = ramdisk / "system/etc/fstab.mt6765"
    if args.ramdisk_root:
        require(runtime_fstab)
        etc_link = ramdisk / "etc"
        if not etc_link.is_symlink() or str(etc_link.readlink()).replace("\\", "/") != "/system/etc":
            fail("built ramdisk /etc must remain OrangeFox's /system/etc symlink")
    else:
        product_copy_files = (ROOT / "twrp_A25.mk").read_text(encoding="utf-8")
        if "recovery/root/fstab.mt6765:recovery/root/system/etc/fstab.mt6765" not in product_copy_files:
            fail("device fstab must be staged under system/etc, leaving OrangeFox root/etc symlink intact")
    if android_fstab.read_bytes() != first_stage_fstab.read_bytes():
        fail("root and first-stage Android fstab copies must match")
    android_lines = android_fstab.read_text(encoding="utf-8").splitlines()
    data_entries = [line for line in android_lines if " /data " in line]
    metadata_entries = [line for line in android_lines if " /metadata " in line]
    if len(data_entries) != 1 or len(metadata_entries) != 1:
        fail("Android fs_mgr fstab must define exactly one /data and /metadata entry")
    data_entry = data_entries[0]
    for token in (
        "fileencryption=aes-256-xts:aes-256-cts:v2",
        "keydirectory=/metadata/vold/metadata_encryption",
        "inlinecrypt",
    ):
        if token not in data_entry:
            fail(f"Android fs_mgr /data entry is missing {token}")
    if "resize,," in data_entry:
        fail("Android fs_mgr /data entry has an empty mount option")
    if not metadata_entries[0].startswith("/dev/block/by-name/md_udc "):
        fail("Android fs_mgr /metadata must point to md_udc")

    for mount_point in ("/system_root", "/system_ext", "/vendor", "/product"):
        if not any(f" {mount_point} " in line and "logical" in line and "first_stage_mount" in line for line in android_lines):
            fail(f"Android fs_mgr fstab must first-stage mount logical partition {mount_point}")
    if not any(line.startswith("/dev/block/by-name/userdata /data ") for line in android_lines):
        fail("Android fs_mgr /data must use the userdata physical partition")
    for token in (
        "on post-fs",
        "on property:init.svc.recovery=running",
        "on property:orangefox.postinit.status=1",
        "on property:orangefox.mount_to_decrypt=1",
        "on property:orangefox.a25_vendor.ready=0",
        "start a25_mount_crypto_vendor",
        "service a25_mount_crypto_vendor /sbin/sh /sbin/a25_mount_crypto_vendor.sh",
        "on property:orangefox.a25_vendor.ready=1 && property:init.svc.servicemanager=running",
    ):
        if token not in mt_rc:
            fail(f"early crypto startup prerequisites missing: {token}")
    post_fs_action = mt_rc.split("on post-fs", 1)[1]
    if post_fs_action.index("start a25_mount_crypto_vendor") > post_fs_action.index("symlink /dev/block/sda"):
        fail("crypto vendor helper must start before later post-fs work")
    mount_helper = ramdisk / "sbin/a25_mount_crypto_vendor.sh"
    require(mount_helper)
    mount_helper_text = mount_helper.read_text(encoding="utf-8")
    for token in (
        "/dev/block/mapper/vendor",
        "/vendor",
        "readlink -f",
        "mounted_source",
        "setprop orangefox.a25_vendor.ready 1",
        "chown 1017:1017 /tmp/a25-keystore2-db",
        'getprop orangefox.a25_vendor.ready)" = 1',
    ):
        if token not in mount_helper_text:
            fail(f"early crypto partition helper missing: {token}")
    if "sleep 5" in mount_helper_text:
        fail("crypto vendor startup must not wait on an unconditional five-second delay")

    if args.ramdisk_root and not any(
        path.is_file() and path.stat().st_size for path in (
            ramdisk / "system/etc/recovery.fstab",
        )
    ):
        fail("built recovery must contain recovery.fstab in its staged runtime path")
    if args.ramdisk_root:
        built_twrp_fstab = ramdisk / "system/etc/recovery.fstab"
        require(built_twrp_fstab)
        if built_twrp_fstab.read_bytes() != (ROOT / "recovery.fstab").read_bytes():
            fail("built recovery's /system/etc/recovery.fstab differs from TARGET_RECOVERY_FSTAB")
    if args.ramdisk_root:
        vars_xml = ramdisk / "twres/resources/vars.xml"
        require(vars_xml)
        vars_text = vars_xml.read_text(encoding="utf-8")
        if '<variable name="lock_btn"' not in vars_text:
            fail("built recovery is missing the OrangeFox lock button variable")
        board_config = (ROOT / "BoardConfig.mk").read_text(encoding="utf-8")
        if "OF_USE_LOCKSCREEN_BUTTON := 1" not in board_config:
            fail("A25 build config must compile OrangeFox button unlock as the default")

    for line in (
        "on property:orangefox.mount_to_decrypt=1",
        "start vendor.keymaster-4-1",
        "start vendor.gatekeeper-1-0",
        "on property:orangefox.a25_system.ready=1 && property:init.svc.servicemanager=running",
        "start a25_logd",
        "on property:orangefox.a25_system.ready=1 && property:init.svc.a25_logd=running",
        "start keystore2",
        "on property:init.svc.servicemanager=running",
        "setprop servicemanager.ready true",
        "on property:init.svc.servicemanager=stopped",
        "setprop servicemanager.ready false",
    ):
        if line not in mt_rc:
            fail(f"recovery HAL startup missing: {line}")
    for relative, service in (
        ("system/etc/init/android.hardware.keymaster@4.1-service.rc", "service vendor.keymaster-4-1 /vendor/bin/hw/android.hardware.keymaster@4.1-service"),
        ("system/etc/init/android.hardware.gatekeeper@1.0-service.rc", "service vendor.gatekeeper-1-0 /vendor/bin/hw/android.hardware.gatekeeper@1.0-service"),
    ):
        service_rc = ramdisk / relative
        require(service_rc)
        if service not in service_rc.read_text(encoding="utf-8"):
            fail(f"recovery HAL service definition missing from {relative}")
    keymaster_text = (ramdisk / "system/etc/init/android.hardware.keymaster@4.1-service.rc").read_text(encoding="utf-8")
    if "interface android.hardware.keymaster@3.0::IKeymasterDevice default" not in keymaster_text:
        fail("Keymaster recovery init service must advertise the 3.0 interface requested by hwservicemanager")
    crypto_mount_text = (ROOT / "recovery/root/sbin/a25_mount_crypto_vendor.sh").read_text(encoding="utf-8")
    for token in (
        "ensure_system_ro()",
        "mount -t ext4 -o ro",
        "printf '%s\\n' \"$DATA_FSTAB_ROW\" > \"$STAGED_ADDITIONAL_FSTAB\"",
        "mount -o bind \"$STAGED_ADDITIONAL_FSTAB\" \"$ADDITIONAL_FSTAB\"",
        'cp "$STAGED_ADDITIONAL_FSTAB" "$ADDITIONAL_FSTAB"',
        'printf \'%s\\n\' additional-fstab-created > "$STATUS_FILE"',
        "chown 1017:1017 /tmp/a25-keystore2-db",
        "metadata_encryption=aes-256-xts",
        "setprop orangefox.a25_system.ready 1",
    ):
        if token not in crypto_mount_text:
            fail(f"recovery crypto bootstrap missing: {token}")

    fbe_patch = (ROOT / "patches/a25-preserve-fbe-on-de-key-failure.patch").read_text(encoding="utf-8")
    for token in (
        "bool fbe_metadata_ready = false;",
        "if (!fbe_metadata_ready)",
        "refusing legacy FDE decryption",
        "data_partition->Key_Directory.empty()",
        "tw_fbe_de_keys_ready",
    ):
        if token not in fbe_patch:
            fail(f"FBE fallback protection missing: {token}")

    board_config = (ROOT / "BoardConfig.mk").read_text(encoding="utf-8")
    vendor_setup = (ROOT / "vendorsetup.sh").read_text(encoding="utf-8")
    if "export OF_USE_LOCKSCREEN_BUTTON=1" not in vendor_setup:
        fail("OrangeFox lockscreen must use the built-in button unlock option")
    input_blacklist = re.search(
        r'^TW_INPUT_BLACKLIST\s*:=\s*"([^"\\]+)"\s*$',
        board_config,
        re.MULTILINE,
    )
    if not input_blacklist or input_blacklist.group(1) != "mtk-tpd":
        fail("recovery input blacklist must be the single exact device name mtk-tpd")
    if "TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery.fstab" not in board_config:
        fail("TARGET_RECOVERY_FSTAB must point to the OrangeFox-format recovery.fstab")
    if (ROOT / "recovery/root/system/etc/twrp.fstab").exists():
        fail("duplicate OrangeFox fstab source at system/etc/twrp.fstab")
    if "TW_SKIP_ADDITIONAL_FSTAB := true" not in board_config:
        fail("OrangeFox must use the device-tree crypto fstab without ROM-fstab override")
    product_mk = (ROOT / "twrp_A25.mk").read_text(encoding="utf-8")
    if "recovery/root/system/etc/additional.fstab:recovery/root/system/etc/additional.fstab" not in product_mk:
        fail("the corrected fs_mgr additional.fstab must be packaged before Recovery startup")
    if "resize,," in fstab:
        fail("Android recovery fstab contains an empty mount option")
    if "TW_EXCLUDE_MTP := true" in board_config:
        fail("MTP must be included for FunctionFS MTP validation")

    forbidden_payload = (
        # This is the recovery system partition's staging path, not a copy
        # under the ramdisk root. DT init launches it via /system_root/system.
        "bin/keystore2",
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
