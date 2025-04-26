from typing import ClassVar, Optional, Callable, Any
from threading import Lock
from collections import deque


class GlobalStream:
    """
    全局音频缓冲区，用于存储和分发音频数据

    用来将小爱音箱的音频输入输出流，适配到小智 AI 的音频输入输出流
    """

    _instance = None
    _lock = Lock()

    # 默认缓冲区大小（以字节为单位）
    DEFAULT_BUFFER_SIZE = 1024 * 1024  # 1MB

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GlobalStream, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        """初始化实例变量"""
        self._max_buffer_size = self.DEFAULT_BUFFER_SIZE
        self._input_buffer = deque(maxlen=self._max_buffer_size)
        self._is_input_active = False
        self._is_output_active = False
        self._input_readers = {}  # 跟踪每个流的读取位置
        self._reader_counter = 0  # 为每个读取器分配唯一ID
        self._buffer_overflow_count = 0  # 记录缓冲区溢出次数
        self.on_output_data = None  # 输入数据回调函数

    def set_buffer_size(self, frames: int) -> None:
        if frames <= 0:
            raise ValueError("缓冲区大小必须大于0")

        # 创建新的有限长度缓冲区
        new_input_buffer = deque(self._input_buffer, maxlen=frames * 2)

        # 替换旧缓冲区
        self._input_buffer = new_input_buffer
        self._max_buffer_size = frames * 2

        # 重置读取位置，因为缓冲区可能已经改变
        for reader_id in self._input_readers:
            self._input_readers[reader_id] = 0

    def register_reader(self) -> int:
        """注册一个新的读取器并返回其ID"""
        reader_id = self._reader_counter
        self._input_readers[reader_id] = 0  # 初始位置为0
        self._reader_counter += 1
        return reader_id

    def unregister_reader(self, reader_id: int) -> None:
        """注销一个读取器"""
        if reader_id in self._input_readers:
            del self._input_readers[reader_id]

    def read(self, reader_id: int, num_frames: int) -> bytes:
        num_frames = num_frames * 2
        if not self._is_input_active:
            return bytes(num_frames)

        if reader_id not in self._input_readers:
            return bytes(num_frames)

        # 将输入缓冲区转换为列表以便随机访问
        buffer_list = list(self._input_buffer)
        current_pos = self._input_readers[reader_id]

        # 如果当前位置超出缓冲区大小，返回空字节
        if current_pos >= len(buffer_list):
            return bytes(num_frames)

        # 读取数据
        end_pos = min(current_pos + num_frames, len(buffer_list))
        data = bytes(buffer_list[current_pos:end_pos])

        # 更新读取位置
        self._input_readers[reader_id] = end_pos

        # 如果数据不足，用零填充
        if len(data) < num_frames:
            data += bytes(num_frames - len(data))

        return data

    # 转发输出音频流
    def write(self, frames: bytes) -> None:
        """写入数据到输出缓冲区"""
        if not self._is_output_active:
            return

        if self.on_output_data:
            self.on_output_data(frames)

    # 添加输入音频流
    def add_input_data(self, data: bytes) -> None:
        if not self._is_input_active:
            return

        """添加输入数据到全局缓冲区"""
        # 检查是否会溢出
        if len(self._input_buffer) + len(data) > self._max_buffer_size:
            self._buffer_overflow_count += 1

        for b in data:
            self._input_buffer.append(b)

        # 如果有读取器的位置已经超出了缓冲区大小，需要调整
        if len(self._input_buffer) >= self._max_buffer_size:
            for reader_id in self._input_readers:
                if self._input_readers[reader_id] > len(self._input_buffer) // 2:
                    # 将读取位置重置到缓冲区中间，避免读取器永远跟不上
                    self._input_readers[reader_id] = len(self._input_buffer) // 2

    def start_input(self) -> None:
        """启动输入流"""
        self._is_input_active = True

    def stop_input(self) -> None:
        """停止输入流"""
        self._is_input_active = False
        self.clear()

    def start_output(self) -> None:
        """启动输出流"""
        self._is_output_active = True

    def stop_output(self) -> None:
        """停止输出流"""
        self._is_output_active = False

    def is_input_active(self) -> bool:
        """检查输入流是否活跃"""
        return self._is_input_active

    def is_output_active(self) -> bool:
        """检查输出流是否活跃"""
        return self._is_output_active

    def clear(self) -> None:
        """清空缓冲区"""
        self._input_buffer.clear()
        for reader_id in self._input_readers:
            self._input_readers[reader_id] = 0


class MyStream:
    """音频流类，用于读写音频数据"""

    def __init__(
        self,
        rate: int,
        channels: int,
        format: int,
        input: bool = False,
        output: bool = False,
        frames_per_buffer: int = 1024,
        start: bool = True,
    ) -> None:
        self._rate = rate
        self._channels = channels
        self._format = format
        self._frames_per_buffer = frames_per_buffer
        self._is_input = input
        self._is_output = output
        self._is_active = False
        self._is_closed = False

        # 获取全局音频缓冲区
        self._global_buffer = GlobalStream()

        # 注册读取器ID
        self._reader_id = self._global_buffer.register_reader() if input else None

        # 如果需要，启动流
        if start:
            self.start_stream()

    def close(self) -> None:
        """关闭流"""
        if not self._is_closed:
            self.stop_stream()
            if self._is_input and self._reader_id is not None:
                self._global_buffer.unregister_reader(self._reader_id)
            self._is_closed = True

    def is_active(self) -> bool:
        """检查流是否活跃"""
        return self._is_active

    def start_stream(self) -> None:
        """启动流"""
        if not self._is_active and not self._is_closed:
            self._is_active = True
            if self._is_input:
                self._global_buffer.start_input()
            if self._is_output:
                self._global_buffer.start_output()

    def stop_stream(self) -> None:
        """停止流"""
        if self._is_active:
            self._is_active = False
            if self._is_input:
                self._global_buffer.stop_input()
            if self._is_output:
                self._global_buffer.stop_output()

    def read(self, num_frames: int, exception_on_overflow=False) -> bytes:
        """从输入流读取数据"""
        if (
            not self._is_input
            or self._is_closed
            or not self._is_active
            or self._reader_id is None
        ):
            return bytes(num_frames)

        return self._global_buffer.read(self._reader_id, num_frames)

    def write(self, frames: bytes) -> None:
        """写入数据到输出流"""
        if not self._is_output or self._is_closed or not self._is_active:
            return

        self._global_buffer.write(frames)


class MyAudio:
    """PyAudio替代品，用于创建和管理音频流"""

    Stream: ClassVar[type] = MyStream

    def __init__(self, buffer_size: int = GlobalStream.DEFAULT_BUFFER_SIZE) -> None:
        # 初始化全局音频缓冲区
        self._global_buffer = GlobalStream()
        # 设置缓冲区大小
        if buffer_size != GlobalStream.DEFAULT_BUFFER_SIZE:
            self._global_buffer.set_buffer_size(buffer_size)
        self._is_terminated = False

    def open(
        self,
        rate: int,
        channels: int,
        format: int,
        input: bool = False,
        output: bool = False,
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
        frames_per_buffer: int = 1024,
        start: bool = True,
        input_host_api_specific_stream_info: Optional[Any] = None,
        output_host_api_specific_stream_info: Optional[Any] = None,
        stream_callback: Optional[Callable] = None,
    ) -> MyStream:
        """打开一个新的音频流"""
        if self._is_terminated:
            raise RuntimeError("MyAudio instance has been terminated")

        # 启动全局输入/输出流（如果需要）
        if input:
            self._global_buffer.start_input()
        if output:
            self._global_buffer.start_output()

        # 创建并返回一个新的流实例
        return MyStream(
            rate=rate,
            channels=channels,
            format=format,
            input=input,
            output=output,
            frames_per_buffer=frames_per_buffer,
            start=start,
        )

    def terminate(self) -> None:
        """终止MyAudio实例"""
        if not self._is_terminated:
            self._global_buffer.stop_input()
            self._global_buffer.stop_output()
            self._is_terminated = True
