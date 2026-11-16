# Android device tree for iku A25 (A25)

`recovery.fstab` is the TWRP-format table selected by `TARGET_RECOVERY_FSTAB`.
OrangeFox stages it at `/system/etc/recovery.fstab`; `/etc/recovery.fstab`
resolves there through a ramdisk symlink. Android fs_mgr uses the separate
`recovery/root/fstab.mt6765` copies.

`fstab.mt6765` carries Android fs_mgr configuration at `/fstab.mt6765`,
`/system/etc/fstab.mt6765`, and `/first_stage_ramdisk/fstab.mt6765`; OrangeFox's
`/etc` symlink exposes the system copy at `/etc/fstab.mt6765`. `/data` maps to userdata (p35) with
FBE v2 key directory `/metadata/vold/metadata_encryption`; `/metadata` maps to
`md_udc` (p10). `inlinecrypt` and `latemount` stay in the Android fs_mgr table.
The OrangeFox `/data` entry also declares the metadata cipher as AES-256-XTS so
its FBEv2 metadata decrypt path receives the algorithm explicitly.
The full-build setting `TW_SKIP_ADDITIONAL_FSTAB := true` makes OrangeFox skip
the ROM's extra vendor fstab. OrangeFox's startup log on the flashed build
shows it still loads `/etc/additional.fstab`, so the compile-time setting must
be included in the next full build. The vendor-generated file repeats
`/data` and `/metadata` and its `/data` line contains the malformed `resize,,`
option. The device-tree Android `fstab.mt6765` has that empty mount option
removed; `/data` and `/metadata` are defined once in each consumer's proper
table.

The verified userdata block is `/dev/block/mmcblk0p35`; metadata is
`/dev/block/mmcblk0p10` (`md_udc`). System and vendor are logical partitions.
OrangeFox mounts vendor read-only before starting the Keymaster and Gatekeeper
HALs. Device init does not explicitly start Keystore2; FBE recovery uses the
Keymaster and Gatekeeper HALs.

The recovery helper remounts logical vendor read-only after OrangeFox post-init,
because OrangeFox can unmount its early vendor mount during recovery startup.
System mounts remain owned by OrangeFox. Keymaster advertises HIDL 3.0/4.0/4.1
through its service rc; the local ramdisk packer injects this rc so hwservicemanager
can start it.

MT6765 MTP extends OrangeFox's configfs gadget with an MTP FunctionFS function.
On `mtp,adb`, init starts `adbd` before the deferred binder waits for both
FunctionFS `ep1` endpoints. The helper publishes MTP state only after binding
`ffs.adb` and `ffs.mtp`; endpoint or configfs failures switch back to adb-only
and record the result in `/tmp/mtp_rebind.status`, outside USB property policy.
Run the local transition simulator and layout checks with:

```
python3 tools/test_crypto_vendor_mount.py
python3 tools/test_mtp_rebind.py
python3 tools/verify_recovery_layout.py
```

The crypto mount helper starts at `post-fs`, has no fixed startup delay, and
keeps an already-mounted vendor partition ready across duplicate init triggers.
Its local simulator covers an already-ready mount and a mapper that appears
after startup.
The MTP simulator covers successful binding, MTP/ADB endpoint timeouts,
configfs link failure, and an unavailable ADB endpoint during recovery.

The supplied QTI `haydn` reference starts `qseecomd` and waits for `/dev/qseecom`
before starting Keymaster and Gatekeeper. A25 uses MediaTek Keymaster 4.1 and
Gatekeeper 1.0; only the early-start ordering is applicable. The reference also
uses `wrappedkey_v0` and `inlinecrypt_optimized`, while A25's shipped vendor
fstab does not, so those QTI-specific userdata flags are not part of A25's
recovery fstab.

The latest failed system boot left a pstore kernel panic in `wlan_drv_gen4m`
teardown (`rmmod` → `wiphy_unregister` → `klist_del`). This is separate from
the recovery fstab path; the kernel panic is the current cause indicated by
the captured logs for returning to recovery instead of Android.

```
#
# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#
```
