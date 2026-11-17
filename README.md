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
the ROM's extra vendor fstab. The recovery image therefore packages the
corrected fs_mgr `/data` row as `/system/etc/additional.fstab`, available at
`/etc/additional.fstab` before OrangeFox initializes encrypted userdata. The
crypto helper also creates this file if it is absent. This avoids using the
vendor-generated row, which repeats `/data` and `/metadata` and has a malformed
`resize,,` option. The Android `fstab.mt6765` keeps the empty mount option
removed and remains separate from both Recovery fstab formats.

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

The external SD MTP path has now been confirmed on the connected A25: Windows
enumerates `Micro SDCard` and reports 58.2 GB total / 35.1 GB available. FBE
remains under investigation. Captured logs showed the mounted system's API 36
Keystore2 failing against Recovery's API 32 servicemanager (`Stability` level
0 and `android.security.compat` missing). A local probe with Recovery's API 32
Keystore2 completed shared-secret negotiation, then stopped at service
registration because the booted Recovery VINTF root did not declare its AIDL
service. The next local candidate uses the Recovery Keystore2 binary, a
libvintf 4.0 framework root plus the existing Keystore2 AIDL fragment, and
sets `servicemanager.ready` from init. The duplicate Keymaster device fragment
was removed from the framework fragment directory; the mounted vendor
partition already declares Keymaster 4.1.

Recovery currently starts the vendor's software Gatekeeper and the generic
software Keymaster implementation. The locally patched image
`pending/local-verify/a25-recovery-local/recovery-fbe-compat32-candidate.img`
(SHA-256 `301ea0108ce2c796c4a34d1476b6ccc2a7a2a97e4692cd6d8a9e951f10a36379`)
was signed, AVB-verified, and flashed to the recovery partition from bootloader
on the verified A25 serial. After a clean boot, Gatekeeper and Keymaster stayed
running, Keystore2 registered its AIDL service and remained alive with crash
count 0, and shared-secret negotiation succeeded. The PIN has not yet been
entered; the next check is the user's on-device unlock attempt. Boot logs and
Binder state are saved under `pending/local-verify/a25-recovery-local/` with
the `a25-compat32-boot-` prefix.

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

## Latest FBE runtime evidence (2026-11-17)

The external SD now enumerates in Windows Explorer as `A25 > Micro SDCard`
(58.2 GB total, 35.1 GB available). The running local recovery has the corrected
single-row `/etc/additional.fstab`; metadata decryption succeeds and creates
`/dev/block/dm-3`, which is mounted at `/data`.

The automatic startup attempt fails before PIN verification. The recovery log shows three failed
`fscrypt_initialize_systemwide_keys` attempts after `Trying with wrappedkey`,
then `Unable to decrypt FBE device`. Keystore2 AIDL is registered and stable
with crash count 0, but Keystore2 selects SOFTWARE Keymaster. The vendor Gatekeeper service loads `SoftGatekeeper`, and
the vendor image contains `libpuresoftkeymasterdevice.so` without a secure
Keymaster MTEE/Trustonic service or matching TEE Gatekeeper implementation.
The kernel starts Trusty/MTEE components, but the matching vendor userspace
services and init fragments are absent from the mounted vendor image. This HAL
inventory is not by itself the cause of the current DE key install failure.

The stock vendor `/data` fstab row uses FBE v2 and does not declare
`wrappedkey_v0`; do not infer that flag from Recovery's `Trying with wrappedkey`
diagnostic. A local experiment synced Keymaster's OS properties from the mounted
Android 16 `system/build.prop` before starting the HAL. The runtime snapshot
showed release 16 / SDK 36 / patch 2025-12-01, but DE key initialization still
failed, so that property sync did not resolve the remaining failure. A later
live property read showed release 12 again, indicating an additional property
writer or startup-order issue.

Current complete logs and image audit are under
`pending/local-verify/a25-recovery-local/`, especially `a25-property-runtime-recovery.log`,
`a25-property-runtime-recovery-logcat.txt`,
`a25-property-runtime-recovery-dmesg.txt`, and
`recovery-fbe-version-runtime-report.json`. At the time those startup snapshots
were collected no PIN had been submitted; they contain no Gatekeeper PIN-match
evidence.

The user subsequently submitted a PIN through the recovery CLI and still got
Signal 6. Per the user's instruction, logs from that attempt were not used.
Reviewing TeamWin's `android_system_vold` `android-12.1` source shows that the
`Trying with wrappedkey` message is emitted only after key retrieval succeeds
and the first `install_storage_key()` fails; retrying with wrapped keys then
fails as well. Focus the next probe on the fscrypt key-install ioctl and its
errno. TeamWin's `android_bootable_recovery` `android-12.1` source also shows
that `Decrypt_Device()` falls into the legacy FDE `cryptfs_check_passwd()` path
when `TW_IS_FBE` is false; that interface rejects FBE. The A25 recovery must
preserve FBE classification through the CLI decrypt path and must not treat an
FBE setup failure as an FDE credential check.

An initial source patch is stored at
`patches/a25-preserve-fbe-on-de-key-failure.patch`. It preserves the FBE state
when DE key setup fails, tracks whether those keys are ready, and blocks both
automatic and CLI fallback into the legacy FDE checker. Apply it to a clean
`android_bootable_recovery` checkout with
`tools/apply_fbe_recovery_patch.sh <path-to-bootable-recovery>` before building.
The patch applies cleanly to OrangeFox `fox_12.1` at source commit `8d2aad1`;
it has not yet been built into a recovery image.

```
#
# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#
```


## FBE CLI fallback correction (2026-11-17)

The earlier no-PIN startup evidence shows metadata setup and DE-key initialization are separate stages. The current recovery patch now classifies `/data` as FBE from its configured `keydirectory` before attempting metadata setup, tracks metadata readiness, and returns an explicit FBE error if that setup fails. The CLI decrypt entry point also reconstructs the FBE flag from the `/data` partition before it can reach the legacy FDE checker. This removes a known wrong-path condition; it does not establish that the reported Signal 6 came from that condition or that Gatekeeper accepted the credential. Logs from the latest CLI attempt remain unread by request. The updated patch and verifier still require a new Actions build and fresh pre-PIN runtime evidence.


The first Actions attempt for this correction (`44093082574`) applied the patch but failed during `partitionmanager.cpp` compilation. The CLI hunk had zero context and was placed at the file tail by `git apply`, producing syntax errors near line 4978. The patch is now regenerated with surrounding source context; the incremental diff applies cleanly against an LF copy of the OrangeFox source snapshot. The next Actions run must confirm the complete patch and C++ build before flashing.

### Duplicate FBE patch hunk correction (2026-11-17)

Actions run `44101136523` reached 94% and failed compiling `partitionmanager.cpp` at lines 4997–5010. The patch retained stale zero-context incremental hunks alongside the corrected context hunks, so the stale additions landed at end-of-file. No image was produced. The patch is now regenerated as one unified diff from OrangeFox source HEAD `8d2aad1`; applying it in a clean detached worktree and checking the resulting C++ diff both pass. The static verifier's source-tree mode stops on the build-generated `keystore2.rc`; the Actions verifier checks the extracted build ramdisk. Next: dispatch a new GitHub build after committing this patch, then investigate the reported Android boot failure first with read-only state checks. Logs from the latest CLI decrypt attempt remain unread.

### Recovery loop and system FBE baseline (2026-11-17)

When A25 kept returning to Recovery, `/dev/block/by-name/para` contained a standard BCB request (`boot-recovery` at offset 0, `recovery\n` at `0x40`). Back up the 2 KiB BCB, clear only that region, and preserve the rest of `para`; the device returned to Android. Check BCB state before branching into boot-image theories.

Normal Android baseline: Android 12 completed boot with `ro.crypto.type=file`, metadata encryption enabled, `/data` on `dm-48` with `inlinecrypt`, Keystore2 and Keymaster 4.1 running, Gatekeeper 1.0 running, and user 0 `RUNNING_UNLOCKED`. Use these facts to compare the Recovery crypto path. Logs from the latest CLI decrypt attempt were not inspected.

### Additional fstab missing on Recovery startup (2026-11-18)

A fresh Recovery boot on the connected A25 logged `Skipping Additional Fstab Processing`, had `fstab.additional=0`, and had no `/etc/additional.fstab`. Startup then reported `Unable to decrypt metadata encryption`; this boot never reached the DE-key install stage. The helper's old behavior waited five seconds for a file that `TW_SKIP_ADDITIONAL_FSTAB := true` intentionally prevents OrangeFox from generating, then returned success with a `waiting-for-additional-fstab` status. This is a concrete ordering/configuration failure ahead of the previously observed DE-key failure.

The corrected one-row fs_mgr file is now staged at `recovery/root/system/etc/additional.fstab` and added to `PRODUCT_COPY_FILES`, so `/etc/additional.fstab` exists before OrangeFox parses encrypted userdata. The helper also creates it immediately if missing and validates its contents before publishing system-ready. A temporary live run of the modified helper on A25 created the expected row, returned 0, and left Keymaster, Gatekeeper, and Keystore2 running. No Recovery PIN was entered and no second decrypt was triggered.

Fresh no-PIN logcat confirms Keymaster 4.1 and Gatekeeper 1.0 HIDL registration, successful Keystore2 shared-secret negotiation and AIDL service registration, and `keystore.crash_count=0`; the three service processes remained running in a second snapshot 30 seconds later. Recovery Gatekeeper has not yet had a credential match. WSL crypto-helper, MTP, and recovery-layout checks pass. Next: commit this fstab bootstrap correction, build with GitHub Actions, verify the produced ramdisk contains the packaged file, then test its startup DE path from the Recovery image.
