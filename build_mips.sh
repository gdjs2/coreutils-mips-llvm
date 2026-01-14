#!/bin/bash

set -e

CLANG_DIR="/opt/llvm"
WORK_DIR="/workspace/coreutils"
BUILD_DIR="${WORK_DIR}/build-mips"
OUTPUT_DIR="/workspace/build-output-mips"

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--output-dir <path>]"
            exit 1
            ;;
    esac
done

if ! OUTPUT_DIR=$(realpath "$OUTPUT_DIR" 2>/dev/null); then
    OUTPUT_DIR=$(cd "$OUTPUT_DIR"; pwd)
fi

OUTPUT_STRIPPED="${OUTPUT_DIR}/stripped"
OUTPUT_NONSTRIPPED="${OUTPUT_DIR}/nonstripped"

cd "${WORK_DIR}"

if [ ! -f "configure" ]; then
    echo ""
    echo "Configure script not found. Running bootstrap..."
    echo "------------------------------------------------"
    ./bootstrap
fi

if [ -d "${BUILD_DIR}" ]; then
    echo "Cleaning previous build directory..."
    rm -rf "${BUILD_DIR}"
fi

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

echo ""
echo "Configuring coreutils for MIPS32..."
echo "-----------------------------------"

export CC="${CLANG_DIR}/bin/clang"
export CXX="${CLANG_DIR}/bin/clang++"
export AR="${CLANG_DIR}/bin/llvm-ar"
export AS="${CLANG_DIR}/bin/llvm-as"
export LD="${CLANG_DIR}/bin/ld.lld"
export RANLIB="${CLANG_DIR}/bin/llvm-ranlib"
export STRIP="${CLANG_DIR}/bin/llvm-strip"

export CFLAGS="--target=mips-linux-gnu -march=mips32 -mabi=32 -O2 --gcc-toolchain=/usr"
export CXXFLAGS="${CFLAGS}"
export LDFLAGS="--target=mips-linux-gnu --gcc-toolchain=/usr"

../configure \
    --host=mips-linux-gnu \
    --build=x86_64-linux-gnu \

echo ""
echo "Building coreutils..."
echo "---------------------"

make -j"$(nproc)"

echo ""
echo "Installing non-stripped binaries to ${OUTPUT_NONSTRIPPED}..."
echo "-----------------------------------------------------------"
make install DESTDIR="${OUTPUT_NONSTRIPPED}"

echo ""
echo "Installing stripped binaries to ${OUTPUT_STRIPPED}..."
echo "--------------------------------------------------"
make install DESTDIR="${OUTPUT_STRIPPED}"
find "${OUTPUT_STRIPPED}/usr/local/bin" -type f -exec "${STRIP}" {} \;

echo ""
echo "Cleaning build directory..."
echo "--------------------------"
rm -rf "${BUILD_DIR}"

echo ""
echo "========================================="
echo "Build completed successfully!"
echo "========================================="
echo "Nonstripped binaries: ${OUTPUT_NONSTRIPPED}/usr/local/bin"
echo "Stripped binaries:    ${OUTPUT_STRIPPED}/usr/local/bin"

echo ""
echo "To verify:"
echo "  file ${OUTPUT_NONSTRIPPED}/usr/local/bin/ls"
echo "  file ${OUTPUT_STRIPPED}/usr/local/bin/ls"
echo "  ${CLANG_DIR}/bin/llvm-readelf -h ${OUTPUT_STRIPPED}/usr/local/bin/ls | grep -E '(Machine|Flags)'"
