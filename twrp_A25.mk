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
    fscryptpolicyget.recovery \
    android.hardware.keymaster@4.1-service \
    android.hardware.gatekeeper@1.0-service \
    libkeymaster4_vendor \
    libkeymaster41_vendor \
    libkeymaster4support_vendor \
    libkeymaster_messages_vendor \
    libkeymaster_portable_vendor \
    libpuresoftkeymasterdevice_vendor \
    libcppbor_external_vendor

# keymaster/gatekeeper HAL rc files (non-ELF, safe for COPY_FILES)
PRODUCT_COPY_FILES += \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc:recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc:recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc

# Force the HAL modules into the RECOVERY ramdisk.
# TARGET_RECOVERY_DEVICE_MODULES is appended to TWRP_REQUIRED_MODULES in
# bootable/recovery/Android.mk (line 616) — the correct mechanism. Plain
# PRODUCT_PACKAGES installs to system image only (verified: libkeymaster41
# went to symbols/system/lib64, not recovery/root).
TARGET_RECOVERY_DEVICE_MODULES += \
    android.hardware.keymaster@4.1-service \
    android.hardware.gatekeeper@1.0-service \
    libkeymaster4_vendor \
    libkeymaster41_vendor \
    libkeymaster4support_vendor \
    libkeymaster_messages_vendor \
    libkeymaster_portable_vendor \
    libpuresoftkeymasterdevice_vendor \
    libcppbor_external_vendor

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="full_r65v3_pmz_w1a-user 12 SP1A.210812.016 mp1V15240 release-keys"

BUILD_FINGERPRINT := iku/A25/A25:12/SP1A.210812.016/mp1V15240:user/release-keys
