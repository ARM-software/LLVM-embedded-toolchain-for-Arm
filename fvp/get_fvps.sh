#!/bin/bash

# SPDX-FileCopyrightText: Copyright 2024 Arm Limited and/or its affiliates <open-source-office@arm.com>

# This script downloads the FVP models which we use for testing the toolchain.
# These are available at no cost, but come with EULAs which must be agreed to
# before running them. When run with --non-interactive, this script assumes
# that you agree to these EULAs. If run without that option, the installers for
# some of the packages will present you with the license before installing. The
# AEMv8A and AEMv8R packages do not have installers, instead they place their
# license into the `fvp/install/license_terms' directory.

set -euxo pipefail

args=$(getopt --options "" --longoptions "non-interactive" -- "${@}") || exit
eval "set -- ${args}"

# Change into the directory containing this script. We'll make
# "download" and "install" subdirectories below that.
cd "$(dirname "$0")"

INSTALLER_FLAGS_CORSTONE=()
INSTALLER_FLAGS_CRYPTO=()

while true; do
    case "${1}" in
        (--non-interactive)
            INSTALLER_FLAGS_CORSTONE=(--i-agree-to-the-contained-eula --no-interactive --force)
            INSTALLER_FLAGS_CRYPTO=(--i-accept-the-end-user-license-agreement --basepath "$PWD/install")
            shift 1
        ;;
        (--)
            shift
            break
        (*)
            exit 1
        ;;
    esac
done

URL_CORSTONE_310='https://developer.arm.com/-/media/Arm%20Developer%20Community/Downloads/OSS/FVP/Corstone-310/FVP_Corstone_SSE-310_11.24_13_Linux64.tgz?rev=c370b571bdff42d3a0152471eca3d798&hash=1E388EE3B6E8F675D02D2832DBE61946DEC0386A'
URL_BASE_AEM_A='https://developer.arm.com/-/cdn-downloads/permalink/Fixed-Virtual-Platforms/FM-11.27/FVP_Base_RevC-2xAEMvA_11.27_19_Linux64.tgz'
URL_BASE_AEM_R='https://developer.arm.com/-/cdn-downloads/permalink/Fixed-Virtual-Platforms/FM-11.27/FVP_Base_AEMv8R_11.27_19_Linux64.tgz'
URL_CRYPTO='https://developer.arm.com/-/cdn-downloads/permalink/Fast-Models-Crypto-Plug-in/FM-11.27/FastModels_crypto_11.27.019_Linux64.tgz'

mkdir -p download
pushd download
DOWNLOAD_DIR="$(pwd)"
wget --content-disposition --no-clobber "${URL_CORSTONE_310}"
wget --content-disposition --no-clobber "${URL_BASE_AEM_A}"
wget --content-disposition --no-clobber "${URL_BASE_AEM_R}"
wget --content-disposition --no-clobber "${URL_CRYPTO}"
popd

mkdir -p install
pushd install

if [ ! -d "Corstone-310" ]; then
tar -xf ${DOWNLOAD_DIR}/FVP_Corstone_SSE-310_11.24_13_Linux64.tgz
./FVP_Corstone_SSE-310.sh --destination ./Corstone-310 "${INSTALLER_FLAGS_CORSTONE[@]}"
fi

if [ ! -d "Base_RevC_AEMvA_pkg" ]; then
tar -xf ${DOWNLOAD_DIR}/FVP_Base_RevC-2xAEMvA_11.27_19_Linux64.tgz
# (Extracted directly into ./Base_RevC_AEMvA_pkg/, no installer)
fi

if [ ! -d "AEMv8R_base_pkg" ]; then
tar -xf ${DOWNLOAD_DIR}/FVP_Base_AEMv8R_11.27_19_Linux64.tgz
# (Extracted directly into ./AEMv8R_base_pkg/, no installer)
fi

if [ ! -d "FastModelsPortfolio_11.27" ]; then
tar -xf ${DOWNLOAD_DIR}/FastModels_crypto_11.27.019_Linux64.tgz
# SDDKW-93582: Non-interactive installation fails if cwd is different.
pushd FastModels_crypto_11.27.019_Linux64
# This installer doesn't allow providing a default path for
# interactive installation. The user will have to enter the install
# directory as the target by hand.
./setup.bin "${INSTALLER_FLAGS_CRYPTO[@]}"
popd
fi

popd
