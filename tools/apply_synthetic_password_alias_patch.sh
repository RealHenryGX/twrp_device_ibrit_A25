#!/sbin/sh
set -eu

PATCH=${A25_SYNTHETIC_PASSWORD_PATCH:-/system/etc/a25-fix-synthetic-password-alias.patch}
VOLD=${A25_SYNTHETIC_PASSWORD_VOLD:-/system/vold}
HEADER="$VOLD/KeystoreInfo.hpp"
PATCH_FILE=${A25_PATCH_BIN:-$(command -v patch)}

if [ ! -f "$PATCH" ] || [ ! -f "$HEADER" ]; then
    echo "missing A25 synthetic-password alias patch input" >&2
    exit 1
fi

if grep -q '^#define SYNTHETIC_PASSWORD_KEY_PREFIX "USRSKEY_synthetic_password_"$' "$HEADER"; then
    echo "synthetic-password alias patch already applied"
    exit 0
fi

grep -q '^#define SYNTHETIC_PASSWORD_KEY_PREFIX "synthetic_password_"$' "$HEADER"
"$PATCH_FILE" --batch -p0 "$HEADER" < "$PATCH"
grep -q '^#define SYNTHETIC_PASSWORD_KEY_PREFIX "USRSKEY_synthetic_password_"$' "$HEADER"
echo "synthetic-password alias patch applied"
