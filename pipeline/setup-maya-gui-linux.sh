#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Install full desktop Maya 2027 in the Rocky Linux GUI-test container.
set -euo pipefail

archive=${1:?Pass the path to Autodesk_Maya_2027_Linux_64bit.tgz}
diagnostics=${MAYA_SETUP_DIAGNOSTICS_DIR:?Set MAYA_SETUP_DIAGNOSTICS_DIR}
mkdir -p "$diagnostics"
exec > >(tee "$diagnostics/maya-install.log") 2>&1

echo "c713ce176972268284a740bff6d346e01e03511c9bf0f090128f63f001ac8cf6  $archive" |
    sha256sum --check

dnf install -y epel-release
dnf config-manager --set-enabled crb
dnf install -y \
    xorg-x11-server-Xvfb xorg-x11-xauth dbus-x11 at-spi2-core \
    mesa-dri-drivers mesa-libGL mesa-libGLU mesa-libEGL libglvnd-opengl \
    libxcb xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm \
    libxkbcommon-x11 libX11 libXrender libXi libXrandr libXfixes libXcursor libXinerama \
    libSM libICE libXt libXmu libXp libXpm libXcomposite libXScrnSaver libXdamage \
    libjpeg-turbo libtiff openjpeg2 libva libvdpau \
    alsa-lib nss nspr fontconfig freetype liberation-sans-fonts dejavu-sans-fonts hicolor-icon-theme \
    compat-openssl11 libatomic pcre2-utf16 libaio libnsl libnsl2 \
    pciutils procps-ng which sudo

packages=$(mktemp -d)
trap 'rm -rf "$packages"' EXIT
tar -xzf "$archive" -C "$packages" \
    ./Packages/Maya2027_64-2027.0-16168.x86_64.rpm \
    ./Packages/Licensing/adsklicensing16.0.3.14414-0-0.x86_64.rpm \
    ./Packages/AdskIdentityManager/adskidentitymanager1.16.3.1-1.x86_64.rpm \
    ./Packages/AdpSdk \
    ./Packages/package.tgz

# This shared SDK is a ZIP component rather than an RPM. Maya loads it before
# licensing and otherwise blocks on an "ADP Failed to initialize" error.
# Follow pkg.adp-desktop-sdk.xml's destination and pre/post install actions.
"$packages/Packages/AdpSdk/InstallCustomAction" action=pre
mkdir -p /opt/Autodesk/AdpDesktopSDK/bin
unzip -q "$packages/Packages/AdpSdk/adp-desktop-sdk.zip" -d /opt/Autodesk/AdpDesktopSDK/bin
"$packages/Packages/AdpSdk/InstallCustomAction" action=post

# Install the licensing dependencies first. The RPM creates the service account,
# data directories and Current symlink. A job container has no systemd init, so
# start the same command as Autodesk's service unit, as its service account.
rpm -Uvh \
    "$packages/Packages/AdskIdentityManager/adskidentitymanager1.16.3.1-1.x86_64.rpm" \
    "$packages/Packages/Licensing/adsklicensing16.0.3.14414-0-0.x86_64.rpm"
nohup runuser -u adsklic -- /usr/bin/AdskLicensingService --run \
    > "$diagnostics/adsklicensing.log" 2>&1 < /dev/null &
helper=/opt/Autodesk/AdskLicensing/Current/helper/AdskLicensingInstHelper
ready=false
for _ in {1..30}; do
    if "$helper" list > "$diagnostics/licensed-products.json"; then
        ready=true
        break
    fi
    sleep 1
done
if [[ "$ready" != true ]]; then
    cat "$diagnostics/adsklicensing.log"
    echo "Autodesk Licensing did not start."
    exit 1
fi

# Maya's RPM registers its product with the running licensing service and
# creates bin/maya -> maya2027.
rpm -Uvh "$packages/Packages/Maya2027_64-2027.0-16168.x86_64.rpm"
# The scenes contain Arnold nodes, even though the tests never render. Install
# the bundled MtoA payload and register its module at the vendor's Linux path.
# Use the same extraction approach as setup-runner.py's headless MtoA install.
mtoa=/usr/autodesk/arnold/maya2027
mkdir -p "$mtoa" /usr/autodesk/modules/maya/2027
tar -xzf "$packages/Packages/package.tgz" -C "$mtoa"
sed "s|^+ mtoa any ./|+ mtoa any $mtoa|" "$mtoa/mtoa.mod" \
    > /usr/autodesk/modules/maya/2027/mtoa.mod
test -f "$mtoa/plug-ins/mtoa.so"
test -x /usr/autodesk/maya2027/bin/maya
"$helper" list > "$diagnostics/licensed-products.json"
python3.11 - <<'PY'
import json
import os
from pathlib import Path

products = json.loads(
    (Path(os.environ["MAYA_SETUP_DIAGNOSTICS_DIR"]) / "licensed-products.json").read_text()
)
assert any(
    product.get("feature_id") == "MAYA"
    and str(product.get("sel_prod_ver") or product.get("def_prod_ver", "")).startswith("2027.")
    for product in products
), "Maya 2027 was not registered with Autodesk Licensing"
PY
/usr/autodesk/maya2027/bin/mayapy -c \
    'import maya; import ssl; print("Maya Python runtime:", ssl.OPENSSL_VERSION)'
