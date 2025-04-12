# OpenXiaoAI Patch

> [!CAUTION]
> 刷机有风险，操作需谨慎。

小爱音箱 Pro 补丁固件制作流程：
- 固件提取（登录小米账号获取 OTA 链接）
- 开启固化 SSH（支持自定义登录密码）
- 禁用系统自动更新（系统更新后需要重新刷机打补丁）
- 添加开机启动脚本 `/data/init.sh`（方便执行一些初始化脚本）

## 准备条件

> [!IMPORTANT]
> 本教程仅适用于 **小爱音箱 Pro（LX06）** 和 **Xiaomi 智能音箱 Pro（OH2P）** 这两款机型，**其他型号**的小爱音箱可能存在兼容性问题，请勿直接使用！🚨


- Windows 电脑（需为 x86_64 架构，用于刷机）
- 数据线（不能只是充电线，需要连接到电脑传输数据）
  - Type-C（适用于新款小爱音箱 Pro，无需拆机）
  - Micro USB（旧款小爱音箱 Pro 用这种，需要拆机）


## 下载固件

> [!NOTE]
> 构建版本待发布，敬请期待。


你可以直接在 Github Release 页面下载打包好的补丁固件。

> 默认 SSH 登录密码为 `[REDACTED]`

## 制作固件

或者你也可以按照下面的 2 种方法，制作自定义固件。

### 基础配置

修改 `.env.example` 文件里的配置，然后重命名为 `.env`。

```shell
# 你的小米账号/密码
MI_USER=23333333
MI_PASS=xxxxxxxxx

# 你的小爱音箱名称/DID
MI_DID=小爱音箱Pro

# 你的 SSH 登录密码（默认为 [REDACTED]）
SSH_PASSWORD=[REDACTED]
```

### 1. 使用 Docker 打包固件（推荐）

> [!NOTE]
> Docker 镜像待发布，敬请期待。

```shell
# 使用 Docker 进行构建
docker run -it --rm --env-file $(pwd)/.env -v $(pwd)/assets:/app/assets -v $(pwd)/patches:/app/patches open-xiaoai

# ✅ 打包完成，固件文件已复制到 assets 目录...
# /app/assets/mico_all_92db90ed6_1.88.197/root.squashfs
```

### 2. 本地构建（macOS、Linux）

为了能够正常编译运行该项目，你需要安装以下依赖环境：

- Docker：https://www.docker.com/get-started/
- Python：https://www.python.org/downloads/
- Node.js: https://nodejs.org/zh-cn/download

```bash
# 安装依赖
npm install

# 打包固件
npm run build

# ✅ 打包成功后，原始固件和补丁固件会保存在 assets 目录下
```

> [!TIP]
> 如果你想要更进一步的定制自己的固件，可以参考 `src/build.sh` 脚本里的构建流程：在提取固件后自行修改固件内的脚本、配置和应用程序，然后重新打包即可。

