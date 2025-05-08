#! /bin/sh

set -e

MIN_SPACE_MB=32
DOWNLOAD_BASE_URL="https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-kws"


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


WORK_DIR="$BASE_DIR/open-xiaoai/kws"
KWS_BIN="$WORK_DIR/kws"

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

if [ ! -f "$WORK_DIR/kws" ]; then
    echo "🔥 正在下载模型文件..."
    curl -L -# -o "$WORK_DIR/kws.tar.gz" "$DOWNLOAD_BASE_URL/kws.tar.gz"
    tar -xzvf "$WORK_DIR/kws.tar.gz" -C "$WORK_DIR"
    chmod +x "$KWS_BIN"
    rm "$WORK_DIR/kws.tar.gz"
    echo "✅ 模型文件下载完毕"
fi


CONFIG_DIR="/data/open-xiaoai/kws"
MONITOR_BIN="$CONFIG_DIR/monitor"

if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

if [ ! -f "$MONITOR_BIN" ]; then
    curl -L -# -o "$MONITOR_BIN" "$DOWNLOAD_BASE_URL/monitor"
    chmod +x "$MONITOR_BIN"
fi

if [ ! -f "$CONFIG_DIR/keywords.txt" ]; then
    echo "n ǐ h ǎo x iǎo zh ì @你好小智" >> "$CONFIG_DIR/keywords.txt"
    echo "d òu b āo d òu b āo @豆包豆包" >> "$CONFIG_DIR/keywords.txt"
    echo "✅ 默认关键词已创建"
fi

echo "🔥 正在启动唤醒词识别服务..."

kill -9 `ps|grep "open-xiaoai/kws/monitor"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true
"$MONITOR_BIN" &

kill -9 `ps|grep "open-xiaoai/kws/kws"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true
"$KWS_BIN" \
    --model-type=zipformer2 \
    --tokens="$WORK_DIR/models/tokens.txt" \
    --encoder="$WORK_DIR/models/encoder.onnx" \
    --decoder="$WORK_DIR/models/decoder.onnx" \
    --joiner="$WORK_DIR/models/joiner.onnx" \
    --keywords-file="/data/open-xiaoai/kws/keywords.txt" \
    --provider=cpu \
    --num-threads=1 \
    --chunk-size=1024 \
    noop
