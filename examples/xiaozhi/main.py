import logging
import signal
import sys

from xiaozhi.services.audio.setup import setup_opus
from xiaozhi.utils.logging_config import setup_logging
from xiaozhi.xiaoai import XiaoAI
from xiaozhi.xiaozhi import XiaoZhi

logger = logging.getLogger("Main")


def main():
    setup_opus()
    logger.info("应用程序已启动，按Ctrl+C退出")
    XiaoZhi.instance().run()
    return 0


def setup_graceful_shutdown():
    def signal_handler(_sig, _frame):
        XiaoZhi.instance().shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    XiaoAI.setup_mode()
    setup_logging()
    setup_graceful_shutdown()
    sys.exit(main())
