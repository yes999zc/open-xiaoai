import logging


def setup_logging():
    """配置日志系统"""

    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # 设置根日志级别

    # 清除已有的处理器（避免重复添加）
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # 添加处理器到根日志记录器
    root_logger.addHandler(console_handler)

    # 设置特定模块的日志级别
    logging.getLogger("XiaoZhi").setLevel(logging.INFO)
    logging.getLogger("WebsocketProtocol").setLevel(logging.INFO)
