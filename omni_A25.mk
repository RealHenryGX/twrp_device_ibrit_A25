#
# Copyright (C) 2026 The Android Open Source Project
# Copyright (C) 2026 SebaUbuntu's TWRP device tree generator
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from those products. Most specific first.
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)

# Inherit some common Omni stuff.
$(call inherit-product, vendor/omni/config/common.mk)

# Inherit from A25 device
$(call inherit-product, device/ibrit/A25/device.mk)

PRODUCT_DEVICE := A25
PRODUCT_NAME := omni_A25
PRODUCT_BRAND := iku
PRODUCT_MODEL := A25
PRODUCT_MANUFACTURER := ibrit

PRODUCT_GMS_CLIENTID_BASE := android-ibrit

PRODUCT_BUILD_PROP_OVERRIDES += \
    PRIVATE_BUILD_DESC="full_r65v3_pmz_w1a-user 12 SP1A.210812.016 mp1V15240 release-keys"

BUILD_FINGERPRINT := iku/A25/A25:12/SP1A.210812.016/mp1V15240:user/release-keys
