# Open-XiaoAI x Sherpa-ONNX

> [!CAUTION]
> 下面的教程和脚本正在开发整理中，请勿直接使用！🚨

> [!IMPORTANT]
> 本教程仅适用于 **小爱音箱 Pro（LX06）** 和 **Xiaomi 智能音箱 Pro（OH2P）**

小爱音箱自定义唤醒词，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)。

## 刷机

首先按照 [open-xiaoai](https://github.com/idootop/open-xiaoai) 里的教程将小爱音箱刷机，然后 SSH 连接到小爱音箱。

## 安装脚本

在小爱音箱上安装启动脚本，然后重启小爱音响。

```shell
# 下载到 /data/init.sh 开机时自启动
curl -L -o /data/init.sh https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-kws/init.sh
```

## 设置唤醒词

在你的电脑上克隆本项目，然后修改 `my-keywords.txt` 文件里的唤醒词。注意：

- 仅支持中文唤醒词
- 支持多个唤醒词，每行一个

运行以下命令，更新 `keywords.txt` 配置文件：

```shell
# 你可能需要先安装 uv 👉 https://github.com/astral-sh/uv
uv run keywords.py --tokens tokens.txt --output keywords.txt --text my-keywords.txt
```

将更新后的 `keywords.txt`（你的电脑）复制到 `/data/open-xiaoai/kws/keywords.txt`（小爱音箱），然后重启小爱音箱即可。
