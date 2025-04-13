# Node.js Server

[Open-XiaoAI](https://github.com/idootop/open-xiaoai) 的 Node.js 版 Server 端，用来演示小爱音箱接入[MiGPT-Next](https://github.com/idootop/migpt-next)。

## 环境准备

为了能够正常编译运行该项目，你需要安装以下依赖环境：

- Node.js v22.x: https://nodejs.org/zh-cn/download
- Rust: https://www.rust-lang.org/learn/get-started

## 编译运行

> [!NOTE]
> 请先确认你已经将小爱音箱刷机成功，并安装运行了 Rust 补丁程序 [👉 教程](../client-rust/README.md)

```bash
# 启用 PNPM 包管理工具
corepack enable && corepack install

# 安装依赖
pnpm install

# 编译运行
pnpm dev
```

首次运行你需要先配置自己的大模型服务，才能正常获取 AI 回复。

> [!NOTE]
> 你可以在下面的 `onMessage` 函数中，自定义你想要的回复逻辑，更多配置参考 👉 [MiGPT-Next](https://github.com/idootop/migpt-next/tree/main/apps/next)

```typescript
// packages/server-node/migpt/index.ts
import { sleep } from "@mi-gpt/utils";
import { OpenXiaoAI } from "./xiaoai.js";

async function main() {
  await OpenXiaoAI.start({
    openai: {
      model: "gpt-4o-mini",
      baseURL: "https://api.openai.com/v1",
      apiKey: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    async onMessage(_engine, { text }) {
      if (text.startsWith("你好")) {
        await sleep(1000);
        return { text: "你好，很高兴认识你！" };
      }
    },
  });
  process.exit(0);
}

main();
```

## 注意事项

1. 默认 Server 服务端口为 `4399`（比如 ws://192.168.31.227:4399），运行前请确保该端口未被其他程序占用。

2. 默认 Rust Server 在启动时，并没有开启小爱音箱的录音能力。
如果你需要在 Node.js 端正常接收音频输入流，或者播放音频输出流，请将 `src/server.rs` 文件中被注释掉的 `start_recording` 和 `start_play` 代码加回来，然后重新编译运行。

> [!NOTE]
> 本项目只是一个简单的演示程序，抛砖引玉。如果你需要更多的功能，比如唤醒词识别、语音转文字、连续对话等（甚至是对接 OpenAI 的 [Realtime API](https://platform.openai.com/docs/guides/realtime)），可参考本项目代码，自行实现想要的功能。
