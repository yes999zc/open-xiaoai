import os
import sys
import subprocess
import logging

logger = logging.getLogger("Opus")


def setup_opus():
    libs_dir = ""
    lib_path = ""

    logger.info("正在加载 Opus 动态库，请耐心等待...")

    if sys.platform == "win32":
        libs_dir = os.path.dirname(os.path.abspath(__file__))
        lib_path = os.path.join(libs_dir, "opus.dll")
    elif sys.platform == "darwin":
        result = subprocess.check_output(
            "brew list opus | grep libopus.dylib", shell=True
        )
        lib_path = result.decode("utf-8").strip()
        if not lib_path.endswith("libopus.dylib"):
            raise RuntimeError("请先安装 Opus： brew install opus")
        libs_dir = os.path.dirname(lib_path)
    else:
        raise RuntimeError(f"暂不支持 {sys.platform} 平台")

    import ctypes.util

    original_find_library = ctypes.util.find_library

    def patched_find_library(name):
        if name == "opus":
            return lib_path
        return original_find_library(name)

    ctypes.util.find_library = patched_find_library

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(libs_dir)

    os.environ["PATH"] = libs_dir + os.pathsep + os.environ.get("PATH", "")

    ctypes.CDLL(lib_path)
