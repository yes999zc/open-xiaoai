import asyncio

from config import APP_CONFIG
from xiaozhi.ref import get_audio_codec, get_speaker, get_vad, get_xiaoai, get_xiaozhi
from xiaozhi.services.protocols.typing import AbortReason, DeviceState, ListeningMode


class Step:
    idle = "idle"
    on_interrupt = "on_interrupt"
    on_wakeup = "on_wakeup"
    on_tts_start = "on_tts_start"
    on_tts_end = "on_tts_end"
    on_speech = "on_speech"
    on_silence = "on_silence"


class __EventManager:
    def __init__(self):
        self.session_id = 0
        self.current_step = Step.idle
        self.next_step_future = None

    def update_step(self, step: Step, step_data=None):
        if get_xiaoai().mode == "xiaozhi":
            return

        self.current_step = step
        if self.next_step_future:
            get_xiaoai().async_loop.call_soon_threadsafe(
                self.next_step_future.set_result, (step, step_data)
            )
            self.next_step_future = None

    async def wait_next_step(self, timeout=None) -> Step | None:
        current_session = self.session_id

        self.next_step_future = get_xiaoai().async_loop.create_future()

        async def _timeout(timeout):
            idx = 0
            while idx < timeout:
                idx += 1
                await asyncio.sleep(1)
            return ("timeout", None)

        futures = [self.next_step_future]

        if timeout:
            futures.append(get_xiaoai().async_loop.create_task(_timeout(timeout)))

        done, _ = await asyncio.wait(
            futures,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if current_session != self.session_id:
            # 当前 session 已经结束
            return ("interrupted", None)
        return list(done)[0].result()

    def on_interrupt(self):
        """用户打断（小爱同学）"""
        self.session_id = self.session_id + 1
        self.update_step(Step.on_interrupt)
        self.start_session()

    def on_wakeup(self):
        """用户唤醒（你好小智）"""
        self.session_id = self.session_id + 1
        self.update_step(Step.on_wakeup)
        self.start_session()

    def on_tts_end(self):
        """TTS结束"""
        if self.current_step == Step.on_interrupt:
            # 当前 session 已经被打断了，不再处理
            return
        self.session_id = self.session_id + 1
        self.update_step(Step.on_tts_end)
        self.start_session()

    def on_tts_start(self):
        """TTS结束"""
        self.update_step(Step.on_tts_start)

    def on_speech(self, speech_buffer: bytes):
        """检测到声音（开始说话"""
        self.update_step(Step.on_speech, speech_buffer)

    def on_silence(self):
        """检测到静音（说话结束）"""
        self.update_step(Step.on_silence)

    def start_session(self):
        asyncio.run_coroutine_threadsafe(
            self.__start_session(), get_xiaoai().async_loop
        )

    async def __start_session(self):
        if get_xiaoai().mode == "xiaozhi":
            return

        vad = get_vad()
        codec = get_audio_codec()
        speaker = get_speaker()
        xiaozhi = get_xiaozhi()

        # 先取消之前的 VAD 检测和音频输入输出流
        xiaozhi.set_device_state(DeviceState.IDLE)
        await xiaozhi.protocol.send_abort_speaking(AbortReason.ABORT)

        # 小爱同学唤醒时，直接打断
        if self.current_step == Step.on_interrupt:
            return

        # 尝试打开音频通道
        if not xiaozhi.protocol.is_audio_channel_opened():
            xiaozhi.set_device_state(DeviceState.CONNECTING)
            await xiaozhi.protocol.open_audio_channel()

        # 等待 TTS 余音结束
        if self.current_step in [Step.on_tts_end]:
            vad.resume("silence")
            step, _ = await self.wait_next_step()
            if step != Step.on_silence:
                return

        # 检查是否有人说话
        vad.resume("speech")
        step, speech_buffer = await self.wait_next_step(
            timeout=APP_CONFIG["wakeup"]["timeout"]
        )
        if step == "timeout":
            # 如果没人说话，则回到 IDLE 状态
            xiaozhi.set_device_state(DeviceState.IDLE)
            print("👋 已退出唤醒")
            after_wakeup = APP_CONFIG["wakeup"]["after_wakeup"]
            await after_wakeup(speaker)
            return
        if step != Step.on_speech:
            return

        # 开始说话
        await xiaozhi.protocol.send_start_listening(ListeningMode.MANUAL)
        codec.input_stream.input(speech_buffer)  # 追加音频输入片段
        xiaozhi.set_device_state(DeviceState.LISTENING)

        # 等待说话结束
        vad.resume("silence")
        step, _ = await self.wait_next_step()
        if step != Step.on_silence:
            return

        # 停止说话
        await xiaozhi.protocol.send_stop_listening()
        xiaozhi.set_device_state(DeviceState.IDLE)


EventManager = __EventManager()
