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
    adbd.recovery

# keymaster/gatekeeper HAL rc files (non-ELF, safe for COPY_FILES)
# ALSO ship OUR configfs init.recovery.usb.rc WITH the deterministic
# late-init finalize (re-link f1 + UDC rebind + restart adbd). Root
# cause of intermittent USB: startup race between init's configfs setup
# and adbd's ffs re-open — same image enumerates OR not per boot, and a
# lost race kills USB permanently (verified by manual teardown test).
# late-init finalize guarantees the gadget ends bound. This OVERRIDES
# the OFOX-source usb.rc that would otherwise ship (OFOX build includes
# its own configfs usb.rc even with EXCLUDE=true — verified on device).
# Ship the MT6765 init fragment: it mounts the real system/vendor partitions
# and starts the matching stock crypto services from those partitions.
PRODUCT_COPY_FILES += \
    device/ibrit/A25/recovery.fstab:recovery/root/etc/recovery.fstab \
    device/ibrit/A25/recovery/root/init.recovery.usb.rc:recovery/root/init.recovery.usb.rc \
    device/ibrit/A25/recovery/root/init.recovery.mt6765.rc:recovery/root/init.recovery.mt6765.rc \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc:recovery/root/system/etc/init/android.hardware.keymaster@4.1-service.rc \
    device/ibrit/A25/recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc:recovery/root/system/etc/init/android.hardware.gatekeeper@1.0-service.rc

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="full_r65v3_pmz_w1a-user 12 SP1A.210812.016 mp1V15240 release-keys"

BUILD_FINGERPRINT := iku/A25/A25:12/SP1A.210812.016/mp1V15240:user/release-keys
