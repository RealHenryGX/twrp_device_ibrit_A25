#
# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit some common TWRP stuff.
$(call inherit-product, vendor/twrp/config/common.mk)

# Inherit from A25 device
$(call inherit-product, device/ibrit/A25/device.mk)

PRODUCT_DEVICE := A25
PRODUCT_NAME := twrp_A25
PRODUCT_BRAND := iku
PRODUCT_MODEL := A25
PRODUCT_MANUFACTURER := ibrit

PRODUCT_GMS_CLIENTID_BASE := android-ibrit

PRODUCT_PACKAGES += \
    fscryptpolicyget.recovery

# keymaster/gatekeeper HAL rc files (non-ELF, safe for COPY_FILES)
# NOTE: our configfs init.recovery.usb.rc is intentionally NOT shipped.
# OFOX12 (EXCLUDE=true, usb.rc unpackaged) had working USB; OFOX27
# (usb.rc packaged via COPY_FILES + late-init reset) USB dead. TWRP's
# in-code USB init owns the gadget when EXCLUDE=true; a stray configfs
# rc only fights it (dmesg: unregister_gadget loop). Keep EXCLUDE=true
# and DO NOT package usb.rc.
PRODUCT_COPY_FILES += \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc:recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc:recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc

# Force the HAL modules into the RECOVERY ramdisk.
# TARGET_RECOVERY_DEVICE_MODULES is appended to TWRP_REQUIRED_MODULES in
# bootable/recovery/Android.mk (line 616). The Android.bp modules carry
# recovery:true / recovery_available:true so they actually install into
# recovery/root (OFOX21 without them went to vendor/bin/hw + system/lib64).
TARGET_RECOVERY_DEVICE_MODULES += \
    a25_android.hardware.keymaster@4.1-service \
    a25_android.hardware.gatekeeper@1.0-service \
    libkeymaster4_vendor \
    libkeymaster41_vendor \
    libkeymaster4support_vendor \
    libkeymaster4_1support_vendor \
    libkeymaster_messages_vendor \
    libkeymaster_portable_vendor \
    libpuresoftkeymasterdevice_vendor \
    libcppbor_external_vendor

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="full_r65v3_pmz_w1a-user 12 SP1A.210812.016 mp1V15240 release-keys"

BUILD_FINGERPRINT := iku/A25/A25:12/SP1A.210812.016/mp1V15240:user/release-keys
