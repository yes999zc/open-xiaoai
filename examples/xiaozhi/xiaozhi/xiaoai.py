import argparse
import asyncio

import numpy as np
import open_xiaoai_server

from xiaozhi.services.audio.stream import GlobalStream


class XiaoAi:
    mode = "xiaoai"
    loop = asyncio.new_event_loop()

    @classmethod
    def setup_mode(cls):
        parser = argparse.ArgumentParser(
            description="小爱音箱接入小智 AI 演示 | by: https://del.wang"
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
        cls.loop.run_until_complete(future)

    @classmethod
    async def init_xiaoai(cls):
        GlobalStream().on_output_data = cls.on_output_data
        open_xiaoai_server.register_fn("on_input_data", cls.on_input_data)
        await open_xiaoai_server.start_server()
