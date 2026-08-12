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

# Explicitly ship keymaster/gatekeeper HAL into recovery ramdisk.
# recovery/root/system/ subdirs are NOT auto-copied by TWRP build
# (verified: OFOX17 ramdisk lacks them, keystore2 still crashes).
# PRODUCT_COPY_FILES is the reliable mechanism.
PRODUCT_COPY_FILES += \
    device/ibrit/A25/recovery/root/system/bin/hw/android.hardware.keymaster@4.1-service:recovery/root/system/bin/hw/android.hardware.keymaster@4.1-service \
    device/ibrit/A25/recovery/root/system/bin/hw/android.hardware.gatekeeper@1.0-service:recovery/root/system/bin/hw/android.hardware.gatekeeper@1.0-service \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc:recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc:recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc \
    device/ibrit/A25/recovery/root/system/lib64/android.hardware.gatekeeper@1.0.so:recovery/root/system/lib64/android.hardware.gatekeeper@1.0.so \
    device/ibrit/A25/recovery/root/system/lib64/android.hardware.keymaster@3.0.so:recovery/root/system/lib64/android.hardware.keymaster@3.0.so \
    device/ibrit/A25/recovery/root/system/lib64/android.hardware.keymaster@4.0.so:recovery/root/system/lib64/android.hardware.keymaster@4.0.so \
    device/ibrit/A25/recovery/root/system/lib64/android.hardware.keymaster@4.1.so:recovery/root/system/lib64/android.hardware.keymaster@4.1.so \
    device/ibrit/A25/recovery/root/system/lib64/libcppbor_external.so:recovery/root/system/lib64/libcppbor_external.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster4.so:recovery/root/system/lib64/libkeymaster4.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster41.so:recovery/root/system/lib64/libkeymaster41.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster4_1support.so:recovery/root/system/lib64/libkeymaster4_1support.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster4support.so:recovery/root/system/lib64/libkeymaster4support.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster_messages.so:recovery/root/system/lib64/libkeymaster_messages.so \
    device/ibrit/A25/recovery/root/system/lib64/libkeymaster_portable.so:recovery/root/system/lib64/libkeymaster_portable.so \
    device/ibrit/A25/recovery/root/system/lib64/libpuresoftkeymasterdevice.so:recovery/root/system/lib64/libpuresoftkeymasterdevice.so

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="full_r65v3_pmz_w1a-user 12 SP1A.210812.016 mp1V15240 release-keys"

BUILD_FINGERPRINT := iku/A25/A25:12/SP1A.210812.016/mp1V15240:user/release-keys
