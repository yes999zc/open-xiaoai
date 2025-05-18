import threading
import time

import numpy as np

from config import APP_CONFIG
from xiaozhi.event import EventManager
from xiaozhi.ref import set_vad
from xiaozhi.services.audio.stream import MyAudio
from xiaozhi.services.audio.vad.silero import VAD_MODEL
from xiaozhi.services.protocols.typing import AudioConfig
from xiaozhi.utils.base import get_env


class _VAD:
    """基于WebRTC VAD的语音活动检测器，用于检测用户打断"""

    def __init__(self):
        set_vad(self)

        config = APP_CONFIG.get("vad", {})

        # 参数设置
        self.sample_rate = 16000
        self.frame_size = 512
        self.threshold = config.get("threshold", 0.01)
        self.min_speech_duration = config.get("min_speech_duration", 250)
        self.min_silence_duration = config.get("min_silence_duration", 500)

        # 状态变量
        self.paused = True
        self.thread = None
        self.speech_count = 0
        self.silence_count = 0

        # 创建独立的PyAudio实例和流，避免与主音频流冲突
        self.audio = None
        self.stream = None

        # 暂存的语音片段
        self.temp_frames = []
        self.speech_buffer = []
        self.target = None  # 检测目标 speech/silence

    def _reset_state(self):
        """重置状态"""
        self.speech_count = 0
        self.silence_count = 0
        self.speech_buffer = []
        self.temp_frames = []

    def start(self):
        """启动VAD检测器"""
        if not get_env("CLI"):
            return

        if self.thread and self.thread.is_alive():
            return

        self.paused = False

        # 初始化PyAudio和流
        self._initialize_audio_stream()

        # 启动检测线程
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()

    def pause(self):
        """暂停VAD检测"""
        if not get_env("CLI"):
            return

        self.paused = True
        self._reset_state()
        self.stream.stop_stream()

    def resume(self, target: str):
        """恢复VAD检测"""
        if not get_env("CLI"):
            return

        self.paused = False
        self.target = target
        self.stream.start_stream()

    def _handle_speech_frame(self, frames):
        """处理语音帧"""
        self.speech_count += len(frames)
        self.silence_count = 0
        self.speech_buffer.extend(frames)

        speech_bytes = bytes(self.speech_buffer)

        if (
            self.target == "speech"
            and self.speech_count > self.min_speech_duration * self.sample_rate / 1000
        ):
            self.pause()
            EventManager.on_speech(speech_bytes)

    def _handle_silence_frame(self, frames):
        """处理静音帧"""
        self.silence_count += len(frames)
        self.speech_count = 0
        self.speech_buffer = []

        if (
            self.target == "silence"
            and self.silence_count > self.min_silence_duration * self.sample_rate / 1000
        ):
            self.pause()
            EventManager.on_silence()

    def _detect_speech(self, frames):
        """检测是否是语音"""
        try:
            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            speech_prob = VAD_MODEL(audio_float32, 16000).item()
            is_speech = speech_prob >= self.threshold
            return is_speech
        except Exception:
            return False

    def _initialize_audio_stream(self):
        """初始化独立的音频流"""
        try:
            # 创建 PyAudio 实例
            self.audio = MyAudio.create()
            # 创建输入流
            self.stream = self.audio.open(
                format=AudioConfig.FORMAT,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frame_size,
                start=True,
            )
            return True
        except Exception:
            return False

    def _close_audio_stream(self):
        """关闭音频流"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            if self.audio:
                self.audio.terminate()
                self.audio = None

        except Exception:
            pass

    def _detection_loop(self):
        """VAD检测主循环"""
        while True:
            # 如果暂停或者音频流未初始化，则跳过
            if self.paused or not self.stream:
                time.sleep(0.1)
                continue

            # 读取缓冲区音频数据
            frames = self.stream.read(self.frame_size)
            if len(frames) != self.frame_size * 2:
                time.sleep(0.01)
                continue

            # 检测是否是语音
            is_speech = self._detect_speech(frames)
            if is_speech:
                self._handle_speech_frame(frames)
            else:
                self._handle_silence_frame(frames)

            time.sleep(0.01)


VAD = _VAD()
