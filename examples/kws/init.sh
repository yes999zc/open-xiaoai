#! /bin/sh

set -e

MIN_SPACE_MB=32
DOWNLOAD_URL="https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-kws/kws.tar.gz"


check_disk_space() {
    local space_kb=$(df -k "$1" | awk 'NR==2 {print $4}')
    if [ $((space_kb / 1024)) -lt "$MIN_SPACE_MB" ]; then
        echo 1
    else
        echo 0
    fi
}


BASE_DIR="/data"
if [ $(check_disk_space "$BASE_DIR") -eq 1 ]; then
    BASE_DIR="/tmp"
    if [ $(check_disk_space "$BASE_DIR") -eq 1 ]; then
        echo "❌ 磁盘空间不足，请先清理磁盘空间（至少需要 $MIN_SPACE_MB MB 空间）"
        exit 1
    fi
fi


WORK_DIR="$BASE_DIR/open-xiaoai"

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

if [ ! -f "$WORK_DIR/kws/kws" ]; then
    echo "🔥 正在下载模型文件..."
    curl -L -# -o "$WORK_DIR/kws.tar.gz" https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-kws/kws.tar.gz
    tar -xzvf "$WORK_DIR/kws.tar.gz" -C "$WORK_DIR"
    rm "$WORK_DIR/kws.tar.gz"
    echo "✅ 模型文件下载完毕"
fi

echo "🔥 正在启动唤醒词识别服务..."

"$WORK_DIR/kws/kws" \
    --model-type=zipformer2 \
    --tokens="$WORK_DIR/kws/models/tokens.txt" \
    --encoder="$WORK_DIR/kws/models/encoder.onnx" \
    --decoder="$WORK_DIR/kws/models/decoder.onnx" \
    --joiner="$WORK_DIR/kws/models/joiner.onnx" \
    --keywords-file="/data/open-xiaoai/kws/keywords.txt" \
    --provider=cpu \
    --num-threads=1 \
    --chunk-size=1024 \
    noop
