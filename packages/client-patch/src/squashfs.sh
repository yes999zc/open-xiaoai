#!/bin/bash

set -e

BASE_DIR=$(pwd)
WORK_DIR=$BASE_DIR/temp

FIRMWARE=$(basename $(ls $BASE_DIR/assets/*.bin 2>/dev/null | head -n 1) .bin)

cd $WORK_DIR

if [ ! -f "$BASE_DIR/assets/$FIRMWARE.bin" ]; then
    echo "❌ 固件文件不存在，请先下载固件到：$BASE_DIR/assets/"
    exit 1
fi

if [ ! -d "$FIRMWARE" ]; then
    echo "❌ 解压后的固件文件夹不存在，请先提取固件"
    exit 1
fi

SQUASHFS_INFO=$(file $FIRMWARE/root.squashfs)
echo "🚗 原始固件信息: $SQUASHFS_INFO"

COMPRESSION=$(echo "$SQUASHFS_INFO" | grep -o "xz\|gzip\|lzo\|lz4\|zstd compressed" | cut -d' ' -f1)
BLOCKSIZE=$(echo "$SQUASHFS_INFO" | grep -o "blocksize: [0-9]* bytes" | cut -d' ' -f2)

echo "🔥 使用原始参数重新打包固件..."
mksquashfs squashfs-root $FIRMWARE/root.squashfs \
    -comp $COMPRESSION -b $BLOCKSIZE \
    -noappend -all-root -always-use-fragments -no-xattrs -no-exports

cp -rf $FIRMWARE $BASE_DIR/assets/$FIRMWARE

echo "✅ 打包完成，固件文件已复制到 assets 目录..."
echo $BASE_DIR/assets/$FIRMWARE/root.squashfs
