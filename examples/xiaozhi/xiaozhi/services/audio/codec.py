import opuslib_next as opuslib

from xiaozhi.ref import set_audio_codec
from xiaozhi.services.audio.stream import MyAudio
from xiaozhi.services.protocols.typing import AudioConfig


class AudioCodec:
    """音频编解码器类，处理音频的录制和播放"""

    def __init__(self):
        """初始化音频编解码器"""
        self.audio = None
        self.input_stream = None
        self.output_stream = None
        self.opus_encoder = None
        self.opus_decoder = None
        self._is_closing = False

        self._initialize_audio()
        set_audio_codec(self)

    def _initialize_audio(self):
        """初始化音频设备和编解码器"""
        self.audio = MyAudio.create()

        # 初始化音频输入流
        self.input_stream = self.audio.open(
            format=AudioConfig.FORMAT,
            channels=AudioConfig.CHANNELS,
            rate=AudioConfig.SAMPLE_RATE,
            input=True,
            frames_per_buffer=AudioConfig.FRAME_SIZE,
            input_device_index=MyAudio.get_input_device_index(self.audio),
        )

        # 初始化音频输出流
        self.output_stream = self.audio.open(
            format=AudioConfig.FORMAT,
            channels=AudioConfig.CHANNELS,
            rate=AudioConfig.SAMPLE_RATE,
            output=True,
            frames_per_buffer=AudioConfig.FRAME_SIZE,
            output_device_index=MyAudio.get_output_device_index(self.audio),
        )

        # 初始化Opus编码器
        self.opus_encoder = opuslib.Encoder(
            fs=AudioConfig.SAMPLE_RATE,
            channels=AudioConfig.CHANNELS,
            application=opuslib.APPLICATION_AUDIO,
        )

        # 初始化Opus解码器
        self.opus_decoder = opuslib.Decoder(
            fs=AudioConfig.SAMPLE_RATE, channels=AudioConfig.CHANNELS
        )

    def read_audio(self):
        """读取音频输入数据并编码"""
        try:
            data = self.input_stream.read(
                AudioConfig.FRAME_SIZE, exception_on_overflow=False
            )
            if not data:
                return None
            return self.opus_encoder.encode(data, AudioConfig.FRAME_SIZE)
        except Exception:
            return None

    def write_audio(self, opus_data):
        """解码并播放"""
        try:
            pcm_data = self.decode_audio(opus_data)  # 解码
            self.output_stream.write(pcm_data)  # 播放
        except Exception:
            pass

    def decode_audio(self, opus_data, frame_size=AudioConfig.FRAME_SIZE):
        """解码音频数据"""
        return self.opus_decoder.decode(opus_data, frame_size, decode_fec=False)

    def encode_audio(self, buffer, frame_size=AudioConfig.FRAME_SIZE):
        """编码音频数据"""
        try:
            opus_frames = []
            for i in range(0, len(buffer), frame_size * 2):
                chunk = buffer[i : i + frame_size * 2]
                if len(chunk) < frame_size * 2:
                    # 如果 buffer 长度不是 FRAME_SIZE 的 2 倍，需要补齐
                    chunk += b"\x00" * (frame_size * 2 - len(chunk))
                opus_frame = self.opus_encoder.encode(chunk, frame_size)
                opus_frames.append(opus_frame)
            return opus_frames
        except Exception:
            return None

    def start_streams(self):
        """启动音频流"""
        if not self.input_stream.is_active():
            self.input_stream.start_stream()
        if not self.output_stream.is_active():
            self.output_stream.start_stream()

    def stop_streams(self):
        """停止音频流"""
        if self.input_stream.is_active():
            self.input_stream.stop_stream()
        if self.output_stream.is_active():
            self.output_stream.stop_stream()

    def close(self):
        """关闭音频编解码器，确保资源正确释放"""
        if self._is_closing:  # 防止重复关闭
            return
        self._is_closing = True

        try:
            # 关闭输入流
            if self.input_stream:
                try:
                    if self.input_stream.is_active():
                        self.input_stream.stop_stream()
                    self.input_stream.close()
                except Exception:
                    pass
                self.input_stream = None

            # 关闭输出流
            if self.output_stream:
                try:
                    if self.output_stream.is_active():
                        self.output_stream.stop_stream()
                    self.output_stream.close()
                except Exception:
                    pass
                self.output_stream = None

            # 关闭 PyAudio 实例
            if self.audio:
                try:
                    self.audio.terminate()
                except Exception:
                    pass
                self.audio = None

            # 清理编解码器
            self.opus_encoder = None
            self.opus_decoder = None
        except Exception:
            pass
        finally:
            self._is_closing = False
