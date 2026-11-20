#!/bin/bash
set -eu

PATCH=${A25_SYNTHETIC_PASSWORD_PATCH:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../patches" && pwd)/a25-fix-synthetic-password-alias.patch}
VOLD=${1:?usage: apply_synthetic_password_alias_patch.sh <system-vold-checkout>}
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
"$PATCH_FILE" --batch -p1 -d "$VOLD" < "$PATCH"
grep -q '^#define SYNTHETIC_PASSWORD_KEY_PREFIX "USRSKEY_synthetic_password_"$' "$HEADER"
echo "synthetic-password alias patch applied"
