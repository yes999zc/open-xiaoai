import { sleep } from "@mi-gpt/utils";
import { OpenXiaoAI } from "./xiaoai.js";

async function main() {
  await OpenXiaoAI.start({
    openai: {
      model: "gpt-4o-mini",
      baseURL: "https://api.openai.com/v1",
      apiKey: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
    // 默认只会处理以下关键词开头的消息（你也可以自定义），比如：
    // - 请问地球为什么是圆的？
    // - 你知道世界上跑的最快的动物是什么吗？
    callAIKeywords: ["请", "你"],
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
