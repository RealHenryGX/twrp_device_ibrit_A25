# Android device tree for iku A25 (A25)

Recovery framebuffer is 384x854. OrangeFox uses a modular `portrait_hdpi` theme
whose coordinates target 1080x1920. The build workflow scales its horizontal
coordinates to an 864x1920 canvas, matching the panel aspect ratio, and
`TW_CUSTOM_THEME` supplies the OrangeFox modular root UI at
`recovery/theme-a25-864x1920/ui.xml`. Its pages, images, and styles continue to
load from OrangeFox's built theme modules. The verifier checks the scaled
dimensions and required modules in the built ramdisk.

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

## Latest FBE runtime evidence (2026-11-18)

The external SD now enumerates in Windows Explorer as `A25 > Micro SDCard`
(58.2 GB total, 35.1 GB available). The running local recovery has the corrected
single-row `/etc/additional.fstab`; metadata decryption succeeds and creates
`/dev/block/dm-3`, which is mounted at `/data`.

The corrected image from Actions run `44128288715` now packages the additional
fstab before recovery startup. Its pre-PIN boot log shows the metadata-encrypted
partition mapped to `/dev/block/dm-3`, `/data` mounted from that mapper, and
`/system/etc/additional.fstab` containing the single correct A25 userdata row.
The full job log, extracted image evidence, and fresh pre-PIN runtime dumps are
under `pending/local-verify/a25-recovery-local/`.

DE key setup still fails before PIN verification. The specific error is
`Unable to find device keyring: Required key not available` immediately after
`Installed fscrypt key with ref ... to /data`. AOSP's Android init creates a
session keyring named `fscrypt` during its normal fs_mgr FBE mount path; the
OrangeFox recovery path does not run that initialization. The vold retry then
switches to wrapped-key mode even though A25's userdata fstab has no
`wrappedkey_v0`, and its Keystore2 export attempt returns Keymaster error -33
(`KM_ERROR_INVALID_KEY_BLOB`). That -33 is a downstream retry symptom, while
the missing `fscrypt` session keyring is the first failure in this boot.

Keymaster 4.1, Gatekeeper 1.0, and Keystore2 AIDL register and remain running;
Keystore2 crash count is 0. Gatekeeper loads `SoftGatekeeper`, and no
credential-match has been attempted in Recovery. A new source change adds a
small init-stage helper to create the `fscrypt` session keyring before recovery
crypto setup. WSL source checks pass; the helper still needs a GitHub build and
fresh no-PIN runtime validation before asking the user to try Recovery unlock.

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
TeamWin's `android_system_vold` `android-12.1` source shows that the
`Trying with wrappedkey` message is emitted only after the first
`install_storage_key()` call fails. Fresh no-PIN logs from run `44128288715`
now identify that first failure: the session keyring named `fscrypt` is absent
(`Unable to find device keyring: Required key not available`). The wrapped-key
retry then gets Keymaster `-33` from Keystore2. The system-wide DE failure is
therefore already localized before Gatekeeper credential matching. TeamWin's
`android_bootable_recovery` `android-12.1` source also shows
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
The patch applies cleanly to OrangeFox `fox_12.1` at source commit `8d2aad1`
and is present in the successfully built run `44128288715`. Its fresh runtime
evidence shows the remaining DE-key failure is the missing session keyring;
the keyring-init helper is now built and confirmed running on device; it creates the `fscrypt` session keyring. The later metadata failure is in Keymaster blob upgrade, not keyring setup.

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

Fresh no-PIN logcat for that earlier image confirmed Keymaster 4.1 and Gatekeeper 1.0 HIDL registration, successful Keystore2 shared-secret negotiation and AIDL service registration, and `keystore.crash_count=0`; the three service processes remained running in a second snapshot 30 seconds later. Recovery Gatekeeper had not yet had a credential match. The fstab bootstrap correction was subsequently built and device-verified in run `44142444216`; later Keymaster findings and the current patch-level candidate are recorded below.

### Actions 44142444216 and normal-system unlock baseline (2026-11-18)

Actions run `44142444216` built and passed image verification; the resulting image was bootloader-flashed and readback-hash verified. Fresh no-PIN Recovery logs show the fscrypt session keyring helper now runs. Metadata setup then fails during Keystore2 `createOperation`: its `upgrade_keyblob_if_required_with` path reports `Upgrade failed` because Keymaster `upgradeKey` returned `-38` (`KM_ERROR_INVALID_ARGUMENT`). The Recovery service is detected as SOFTWARE (`libpuresoftkeymasterdevice.so`). Keystore2 AIDL remains registered and has no crash; Gatekeeper is software-backed. The run never reached a Recovery credential check.

After the user normally unlocked Android, logs confirmed successful Gatekeeper credential verification and CE-key installation for user 0 (`RUNNING_UNLOCKED`). This is the normal-system comparison baseline, not evidence that the Recovery Keymaster path is equivalent. The vendor init configuration references MTEE Keymaster and `wait_for_keymaster` files that are absent on the mounted vendor partition; the generic Keymaster service is present. Continue by identifying the provider used by normal Android and the required Recovery operation parameters. The user's latest CLI Signal 6 logs remain unread.

### Vendor security-patch alignment candidate (2026-11-20)

Normal Android reports `ro.build.version.security_patch=2025-12-01` and `ro.vendor.build.security_patch=2024-03-05`; `/vendor/build.prop` contains that vendor value. Recovery inherited `ro.vendor.build.security_patch=2099-12-31` from the device-tree build settings, while the crypto helper only synced `ro.build.*` before launching Keymaster. OrangeFox's `prepdecrypt.sh` separately syncs the vendor patch property from `/vendor/build.prop`. The helper now does the same before starting crypto HALs. Its existing WSL verification passes and asserts property-reset ordering. The current authorized Recovery logs still show `2099-12-31`, so the correction has not yet been device-verified; metadata and DE key upgrades succeed in this boot, while CE spblob unwrap fails at Keystore2 `getKeyEntry` with `KEY_NOT_FOUND`.

### Authorized Recovery evidence and display theme (2026-11-20)

The authorized Recovery capture is from serial `0123456789ABCDEF`, product `A25`. The 384x854 framebuffer loaded a 1080x1920 `portrait_hdpi` UI, scaling horizontally by 0.355556 and vertically by 0.444792. Actions run `44764145467` showed that the first custom UI was an old TWRP resource model and referenced image IDs absent from OrangeFox's modular resources. The current local layout correction uses OrangeFox's official modular root from its `fox_12.1` branch at `https://gitlab.com/OrangeFox/bootable/Recovery/-/raw/fox_12.1/gui/theme/portrait_hdpi/ui.xml`, sets an 864x1920 virtual canvas, and scales horizontal positions and widths by 0.8 in the OrangeFox theme during the build. Local transform and source checks pass. This correction is not pushed, built, or device-tested yet.

The same Recovery capture mounted metadata-encrypted `/data` at `/dev/block/dm-3`; Keystore2 upgraded the metadata, unencrypted, and user 0 DE key blobs. Two user 0 credential checks reached Gatekeeper, which emitted `request reenroll` both times; Keystore2, Keymaster, and Gatekeeper remained running, with `keystore.crash_count=0`. CE decryption then failed in `unwrapSyntheticPasswordBlob`: the spblob v2/v3 path returned `KEY_NOT_FOUND` from Keystore2 `getKeyEntry`. There is no Signal 6/backtrace in this capture. This places the remaining failure after credential verification, at locating the CE spblob's KeyStore key; it does not yet identify why that alias is missing.

The Keystore2 lookup calls `KeystoreInfo::getAlias()` and uses SELinux
namespace 103. Android 16 LockSettingsService uses the logical alias
`synthetic_password_<handle>` in that namespace. Keep the upstream alias.
The current Recovery Keystore2 starts with a temporary database so metadata
can be decrypted before userdata is mounted. Access to the installed system
Keystore2 state for credential encrypted storage remains to be validated.
