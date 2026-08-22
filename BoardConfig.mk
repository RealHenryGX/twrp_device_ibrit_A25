#
# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

DEVICE_PATH := device/ibrit/A25

# For building with minimal manifest
ALLOW_MISSING_DEPENDENCIES := true

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 := 
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a53

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv7-a-neon
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a53

# APEX
OVERRIDE_TARGET_FLATTEN_APEX := true

# Bootloader
TARGET_BOOTLOADER_BOARD_NAME := r65v3_pmz_w1a
TARGET_NO_BOOTLOADER := true

# Display
TARGET_SCREEN_DENSITY := 180

# Kernel
BOARD_BOOTIMG_HEADER_VERSION := 2
BOARD_KERNEL_BASE := 0x40078000
BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2 buildvariant=user
BOARD_KERNEL_PAGESIZE := 2048
BOARD_RAMDISK_OFFSET := 0x11a88000
BOARD_KERNEL_TAGS_OFFSET := 0x07808000
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOTIMG_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_KERNEL_IMAGE_NAME := Image
BOARD_INCLUDE_DTB_IN_BOOTIMG := true
BOARD_KERNEL_SEPARATED_DTBO := true
TARGET_KERNEL_CONFIG := A25_defconfig
TARGET_KERNEL_SOURCE := kernel/ibrit/A25

# Kernel - prebuilt
TARGET_FORCE_PREBUILT_KERNEL := true
ifeq ($(TARGET_FORCE_PREBUILT_KERNEL),true)
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/kernel
TARGET_PREBUILT_DTB := $(DEVICE_PATH)/prebuilt/dtb.img
BOARD_MKBOOTIMG_ARGS += --dtb $(TARGET_PREBUILT_DTB)
BOARD_INCLUDE_DTB_IN_BOOTIMG := 
BOARD_PREBUILT_DTBOIMAGE := $(DEVICE_PATH)/prebuilt/dtbo.img
BOARD_KERNEL_SEPARATED_DTBO := 
endif

# Partitions
BOARD_FLASH_BLOCK_SIZE := 131072 # (BOARD_KERNEL_PAGESIZE * 64)
BOARD_BOOTIMAGE_PARTITION_SIZE := 33554432
BOARD_RECOVERYIMAGE_PARTITION_SIZE := 33554432
BOARD_HAS_LARGE_FILESYSTEM := true
BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
BOARD_SUPER_PARTITION_SIZE := 9126805504 # TODO: Fix hardcoded value
BOARD_SUPER_PARTITION_GROUPS := ibrit_dynamic_partitions
BOARD_IBRIT_DYNAMIC_PARTITIONS_PARTITION_LIST := system system_ext vendor product
BOARD_IBRIT_DYNAMIC_PARTITIONS_SIZE := 9122611200 # TODO: Fix hardcoded value

# Platform
TARGET_BOARD_PLATFORM := mt6765

# Recovery
BOARD_INCLUDE_RECOVERY_DTBO := true
TARGET_RECOVERY_PIXEL_FORMAT := BGRA_8888
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# Security patch level
VENDOR_SECURITY_PATCH := 2021-08-01

# Verified Boot
BOARD_AVB_ENABLE := true
BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3
BOARD_AVB_RECOVERY_KEY_PATH := external/avb/test/data/testkey_rsa4096.pem
BOARD_AVB_RECOVERY_ALGORITHM := SHA256_RSA4096
BOARD_AVB_RECOVERY_ROLLBACK_INDEX := 1
BOARD_AVB_RECOVERY_ROLLBACK_INDEX_LOCATION := 1

# Hack: prevent anti rollback
PLATFORM_SECURITY_PATCH := 2099-12-31
VENDOR_SECURITY_PATCH := 2099-12-31
PLATFORM_VERSION := 16.1.0

# TWRP Configuration
TW_THEME := portrait_hdpi
# OF_SCREEN_H/OF_STATUS_H were tried (854/40) — made layout WORSE on the
# tiny panel (theme is 1080x1920-designed; mismatched geometry constants
# break centering more than defaults). Reverted to OFOX defaults.
# TW_EXTRA_LANGUAGES is REQUIRED for TWRP GUI (removing it hangs TWRP on boot
# — font lookup fails). But OrangeFox ships its own fonts AND its ramdisk is
# bigger, so extra-languages' 3.8MB CJK fonts push OFOX over the 32MB limit.
# FOX_VANILLA_BUILD=1 is exported by vendorsetup.sh ONLY for OrangeFox builds,
# so we can split the two builds cleanly.
ifneq ($(FOX_VANILLA_BUILD),1)
    TW_EXTRA_LANGUAGES := true
endif
# Touch + screen-off: ONLY TW_NO_SCREEN_BLANK (keep timeout). Root cause of
# dead touch was gr_fb_blank(true) on the MTK fb notifier -> tpd_suspend ->
# axs_touch re-downloads firmware on every resume -> chip corrupted.
# With TW_NO_SCREEN_BLANK, timeout still fires Set_Brightness("0") (screen
# appears off, backlight off) but skips gr_fb_blank -> no fb notifier -> TP
# never suspends -> touch stays alive; touching restores brightness
# (resetTimerAndUnblank still runs Set_Brightness(orig)). Verified in
# blanktimer.cpp: blank()/checkForTimeout() gate gr_fb_blank behind
# #ifndef TW_NO_SCREEN_BLANK only. Do NOT set TW_NO_SCREEN_TIMEOUT — that
# disables the whole timer (no screen-off at all, user complained).
TW_NO_SCREEN_BLANK := true
# TW_SCREEN_BLANK_ON_BOOT removed — it starts the blank cycle that kills touch.
# Blacklist input devices: hbtp_vm (stylus) + mtk-tpd. Device exposes BOTH
# mtk-tpd (event4) and axs_ts (event3). With both active TWRP reads both ->
# touch explosion. Keeping only mtk-tpd made touch DEAD in recovery (MTK tpd
# needs userspace firmware load that recovery lacks); axs_ts is the GSI
# touch bridge and the working source. Separator must be a SINGLE literal
# backslash-x0a pair as DOUBLE backslash in the makefile (JSON-safe: soong
# variables are JSON; "\\x0a" parses to literal \x0a which C turns into \n
# for events.cpp strtok).
TW_INPUT_BLACKLIST := "hbtp_vm\\x0amtk-tpd"
TW_USE_TOOLBOX := true

# MTK USB: KEEP TW_EXCLUDE_DEFAULT_USB_INIT — verified on device:
# OFOX12 (EXCLUDE set) had working adb; OFOX16/17 (removed) USB dead.
# With EXCLUDE, TWRP skips its legacy android_usb init and our
# init.recovery.usb.rc (configfs + sys.usb.config=adb + start adbd)
# fully owns the gadget. Without it, TWRP legacy init fights configfs.
TW_EXCLUDE_DEFAULT_USB_INIT := true

# MTK battery/thermal: use legacy battery services + custom cpu temp node
TW_USE_LEGACY_BATTERY_SERVICES := true
# thermal_zone3 = mtktscpu (verified on device); note: /sys/devices/virtual/thermal/, not /sys/class/thermal/
TW_CUSTOM_CPU_TEMP_PATH := "/sys/devices/virtual/thermal/thermal_zone3/temp"

# FBE v2 metadata encryption (verified: ro.crypto.state=encrypted, type=file,
# ro.crypto.metadata.encryption=metadata_encryption, /data=dm-48, inlinecrypt)
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
TW_FORCE_KEYMASTER_VER := true
# OrangeFox requires this alongside TW_FORCE_KEYMASTER_VER; device has
# keymaster 4.0/4.1 HALs (verified: /system/lib64/android.hardware.keymaster@4.0/4.1.so)
OF_DEFAULT_KEYMASTER_VERSION := 4.1
TW_HAS_DATA_MEDIA := true
# Brightness: MTK exposes LCD backlight under leds class, not backlight class.
# max_brightness=255 verified on device (/sys/class/leds/lcd-backlight).
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 255
# Size reduction: recovery partition is only 32MB. EXCLUDE_APEX removes
# APEX support code; explicit EXCLUDE_* flags trim tzdata (~1MB), nano,
# bash, zip, MTP (rec/Android.mk checks each independently).
TW_EXCLUDE_APEX := true
TW_EXCLUDE_TZDATA := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_ZIP := true
# MTP ENABLED (user needs it to inspect UI/screenshots on the tiny panel).
# 11.7MB ramdisk headroom available; libtwrpmtp-ffs + ffs.rc fit fine.
# TW_EXCLUDE_MTP removed.
# More size trims: no exfat/fuse, no lpdump/lptools (dynamic-partition
# tools not needed in recovery). NOTE: TW_EXCLUDE_ENCRYPTED_BACKUPS is NOT
# set — OrangeFox recovery binary hard-links libopenaes (ninja: no rule to
# make libopenaes.so.toc when excluded).
TW_NO_EXFAT := true
TW_NO_EXFAT_FUSE := true
TW_EXCLUDE_LPDUMP := true
TW_EXCLUDE_LPTOOLS := true
# NOTE: OF_VANILLA_BUILD is obsolete in current OrangeFox (orangefox.mk:605
# error). FOX_VANILLA_BUILD=1 is exported from vendorsetup.sh instead.
# FOX_EXCLUDE_NANO_EDITOR also dropped (TW_EXCLUDE_NANO covers it).
# NOTE: TW_INCLUDE_FASTBOOTD removed — recovery.img exceeded the 32MB
# partition (34621440 > 33484800); fastbootd (~1.5MB+) is not needed for
# FBE decrypt. Re-add only if partition size allows.
