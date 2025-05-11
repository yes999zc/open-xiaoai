# Open-XiaoAI x 小智 AI

[Open-XiaoAI](https://github.com/idootop/open-xiaoai) 的 Python 版 Server 端，用来演示小爱音箱接入[小智 AI](https://github.com/78/xiaozhi-esp32)。

> [!NOTE]
> 该演示使用的 Python 版小智 AI 客户端基于 [py-xiaozhi](https://github.com/Huang-junsen/py-xiaozhi) 项目，特此鸣谢。

## 环境准备

为了能够正常编译运行该项目，你需要安装以下依赖环境/工具：

- uv：https://github.com/astral-sh/uv
- Rust: https://www.rust-lang.org/learn/get-started

> 如果你是 macOS 系统，还需要手动安装 [Opus](https://opus-codec.org/) 👉 `brew install opus`

## 编译运行

> [!NOTE]
> 请先确认你已经将小爱音箱刷机成功，并安装运行了 Rust 补丁程序 [👉 教程](../../packages/client-rust/README.md)，否则该 Python Server 端启动后收不到音频输入，将无法正常工作。

```bash
# 安装 Python 依赖
uv sync

# 编译运行
uv run main.py
```

如果你只是想体验一下小智 AI，请使用以下命令启动：

```bash
uv run main.py --mode xiaozhi
```

该模式下使用电脑的麦克风和扬声器作为音频输入输出设备，无需连接小爱音箱。

## 配置文件

如果你想使用自己部署的 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)，请更新 `config.py` 文件里的接口地址，然后重启应用。

```py
XIAOZHI_CONFIG = {
    "OTA_URL": "https://2662r3426b.vicp.fun/xiaozhi/ota/",
    "WEBSOCKET_URL": "wss://2662r3426b.vicp.fun/xiaozhi/v1/",
    "WEBSOCKET_ACCESS_TOKEN": "xxxxxxxxxxxxx",
}
```

## 注意事项

首次启动会自动打开小智 AI [管理后台](https://xiaozhi.me/)，然后提供一个验证码用来绑定设备。

请按照提示注册你的小智 AI 账号，然后创建 Agent 绑定设备即可开始体验。

注意：绑定设备成功后，需要重新运行本应用才会生效。

> [!NOTE]
> 本项目只是一个简单的演示程序，抛砖引玉。如果你想要更多的功能，比如唤醒词识别、语音转文字、连续对话等，可以参考开源的 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 项目，借助 Python 丰富的 AI 生态自行实现。
