#! /bin/sh

set -e

DOWNLOAD_BASE_URL="https://gitee.com/idootop/artifacts/releases/download"

WORK_DIR="/data/open-xiaoai/scripts"

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

if [ ! -f "$WORK_DIR/client-boot.sh" ]; then
    curl -L -# -o "$WORK_DIR/client-boot.sh" "$DOWNLOAD_BASE_URL/open-xiaoai-client/boot.sh"
fi

if [ ! -f "$WORK_DIR/kws-boot.sh" ]; then
    curl -L -# -o "$WORK_DIR/kws-boot.sh" "$DOWNLOAD_BASE_URL/open-xiaoai-kws/boot.sh"
fi

kill -9 `ps|grep "open-xiaoai/kws/monitor"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true

sh "$WORK_DIR/kws-boot.sh" --no-monitor > /dev/null 2>&1 &

sh "$WORK_DIR/client-boot.sh"
