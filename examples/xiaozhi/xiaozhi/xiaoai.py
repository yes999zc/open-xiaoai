import argparse
import asyncio
import threading

import numpy as np
import open_xiaoai_server

from xiaozhi.services.audio.stream import GlobalStream
from xiaozhi.utils.base import json_decode


class XiaoAI:
    mode = "xiaoai"
    sync_loop: asyncio.AbstractEventLoop = None
    async_loop: asyncio.AbstractEventLoop = None

    @classmethod
    def setup_mode(cls):
        parser = argparse.ArgumentParser(
            description="小爱音箱接入小智 AI | by: https://del.wang"
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=["xiaoai", "xiaozhi"],
            default="xiaoai",
            help="运行模式：【xiaoai】使用小爱音箱的输入输出音频（默认）、【xiaozhi】使用本地电脑的输入输出音频",
        )
        args = parser.parse_args()
        if args.mode == "xiaozhi":
            cls.mode = "xiaozhi"

    @classmethod
    def on_input_data(cls, data: bytes):
        audio_array = np.frombuffer(data, dtype=np.uint16)
        GlobalStream().add_input_data(audio_array.tobytes())

    @classmethod
    def on_output_data(cls, data: bytes):
        async def on_output_data_async(data: bytes):
            return await open_xiaoai_server.on_output_data(data)

        future = on_output_data_async(data)
        cls.sync_loop.run_until_complete(future)

    @classmethod
    async def run_shell(cls, script: str, timeout_millis: float = 10 * 1000):
        return await open_xiaoai_server.run_shell(script, timeout_millis)

    @classmethod
    async def on_event(cls, event: str):
        event_json = json_decode(event) or {}
        event_data = event_json.get("data", {})
        event_type = event_json.get("event")

        if not event_json.get("event"):
            print(f"❌ Event 解析失败: {event}")
            return

        if event_type == "kws":
            if event_data == "Started":
                print("🔥 自定义唤醒词已开启")
                await cls.run_shell("/usr/sbin/tts_play.sh '自定义唤醒词已开启'")
            else:
                keyword = event_data.get("Keyword")
                print(f"🔥 自定义唤醒词: {keyword}")
        elif event_type == "instruction" and event_data.get("NewLine"):
            line = json_decode(event_data.get("NewLine"))
            if (
                line
                and line.get("header", {}).get("namespace") == "SpeechRecognizer"
                and line.get("header", {}).get("name") == "RecognizeResult"
            ):
                text = line.get("payload", {}).get("results")[0].get("text")
                if not text:
                    print("🔥 唤醒小爱同学")
                elif text and line.get("payload", {}).get("is_final"):
                    print(f"🔥 收到用户指令: {text}")

    @classmethod
    def __init_background_event_loop(cls):
        def run_event_loop():
            cls.sync_loop = asyncio.new_event_loop()
            cls.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.async_loop)
            cls.async_loop.run_forever()

        thread = threading.Thread(target=run_event_loop, daemon=True)
        thread.start()

    @classmethod
    def __on_event(cls, event: str):
        asyncio.run_coroutine_threadsafe(
            cls.on_event(event),
            cls.async_loop,
        )

    @classmethod
    async def init_xiaoai(cls):
        GlobalStream().on_output_data = cls.on_output_data
        open_xiaoai_server.register_fn("on_input_data", cls.on_input_data)
        open_xiaoai_server.register_fn("on_event", cls.__on_event)
        cls.__init_background_event_loop()
        await open_xiaoai_server.start_server()
