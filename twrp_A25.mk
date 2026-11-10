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
# Ship the MT6765 init fragment: it mounts the real vendor partition and
# starts the vendor Keymaster/Gatekeeper HALs before keystore2.
PRODUCT_COPY_FILES += \
    device/ibrit/A25/recovery/root/init.recovery.usb.rc:recovery/root/init.recovery.usb.rc \
    device/ibrit/A25/recovery/root/init.recovery.mt6765.rc:recovery/root/init.recovery.mt6765.rc \
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
    a25_keystore2_stock \
    a25_stock_android_hardware_security_keymint_V1_cpp \
    a25_stock_android_hardware_security_keymint_V4_ndk \
    a25_stock_android_system_keystore2_V1_cpp \
    a25_stock_android_system_keystore2_V5_ndk \
    a25_stock_android_hardware_confirmationui_V1_ndk \
    a25_stock_android_hardware_security_secureclock_V1_ndk \
    a25_stock_android_hardware_security_sharedsecret_V1_ndk \
    a25_stock_android_hardware_security_rkp_V3_ndk \
    a25_stock_android_security_compat_ndk \
    a25_stock_lib_android_keymaster_keymint_utils \
    a25_stock_libcppbor \
    a25_stock_libkeymint \
    a25_stock_libkeymint_support \
    a25_stock_libkeystore2_aaid \
    a25_stock_libkeystore2_apc_compat \
    a25_stock_libkeystore2_crypto \
    a25_stock_libkm_compat_service \
    a25_stock_libcxx \
    a25_stock_libsqlite \
    a25_stock_libhidlbase \
    a25_stock_libbinder_ndk \
    a25_stock_libbinder \
    a25_stock_libapexsupport \
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
