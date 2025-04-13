# Rust Client

这是使用 Rust 编写的小爱音箱补丁程序，主要负责：

- 共享通信协议（Server 端和 Client 端实时双向通信）
- 转发小爱音箱的麦克风输入音频流到 Server 端进行识别处理
- 转发小爱音箱上的事件到 Server 端（语音识别结果、播放状态等）
- 响应来自 Server 端的指令调用（执行脚本、播放音频流、系统升级等）

> [!TIP]
> 本项目 Rust 端通过 binding 与 Python 和 Node.js 端双向互调，实现了网络通信模块的共享复用。当然你也可以参考 Rust 端通信协议源码，在其他 Server 端重新实现 WebSocket 通信过程。

## 编译运行

> [!IMPORTANT]
> 本项目只是一个简单的演示程序，抛砖引玉，并未提供任何预构建产物，仅适合有动手能力的人自行编译运行。你可以按需修改源代码，增删自己想要的功能。

首先，你需要在电脑上安装 `Rust` 开发环境 👉 [传送门](https://www.rust-lang.org/)

为了构建能够在小爱音箱上运行的 ARMv7 应用，你还需要安装 `cross` 👉 [传送门](https://github.com/cross-rs/cross)

```shell
# 安装依赖
cargo fetch

# 交叉编译
cross build --release --target armv7-unknown-linux-gnueabihf
```

> [!NOTE]
> 以下操作需要先将小爱音箱刷机， 然后 SSH 连接到小爱音箱。👉 [教程](../../docs/flash.md)

编译成功后，将构建好的补丁程序 `client` 复制到小爱音箱上

```shell
# client 文件路径
./target/armv7-unknown-linux-gnueabihf/release/client
```

如果你是 macOS 系统，可以直接使用 `dd` + `ssh` 命令复制文件到小爱音箱

```shell
dd if=target/armv7-unknown-linux-gnueabihf/release/client \
| ssh -o HostKeyAlgorithms=+ssh-rsa root@你的小爱音箱IP地址 "dd of=/data/client"
```

> 注意：替换你自己的小爱音箱局域网 IP 地址，比如： root@192.168.31.227

你也可以先把 `client` 文件上传到一个地方，然后 SSH 连接到小爱音箱后，再用 `curl` 命令下载到本地。

```shell
# 连接到小爱音箱
ssh -o HostKeyAlgorithms=+ssh-rsa root@你的小爱音箱IP地址

# 下载文件到 /data/client
curl -# -o /data/client https://你的client文件下载链接
```

最后，在小爱音箱上授予 `client` 文件运行权限，然后运行：

```shell
# 授权
chmod +x /data/client

# 运行
/data/client ws://你的 server 端地址（默认使用 4399 端口）

# 比如：/data/client ws://192.168.31.227:4399
```

## 注意事项

当前 Client 端使用 Rust 编写，只负责转发和被动响应 Server 端的调用，不实现具体的业务逻辑。

一方面，小爱音箱的内存算力和存储空间极为有限，语音识别之类的任务并不适合放在 Client 端侧运行。

另一方面，使用 Rust 编写一些业务逻辑，不如 Python 和 Node.js 灵活开发效率高，后者的应用生态也更丰富一些。

> [!CAUTION]
> 当你在公网上运行本项目时，应当提高警惕。🚨

本项目只是一个基础的演示程序，抛砖引玉。诸如多设备连接管理、身份认证、通信数据加密、音频压缩传输等均未做处理。

其默认提供了**执行任意脚本**的能力演示，虽然在启动 Client 端时需要由你本人指定可信的 Server 端连接地址，但还是要务必小心！

毕竟再怎么小心都不为过 :)

你也可以 Fork 本项目，在此基础上将 MiGPT 和小智 AI 等业务逻辑完全放在 Client 端运行，这样就不需要额外的服务器或 NAS 设备来部署运行了。
