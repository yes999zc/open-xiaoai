import json
import logging
import socket
import threading
import uuid
from typing import Any, Optional

import requests

from config import XIAOZHI_CONFIG

logger = logging.getLogger("ConfigManager")


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """确保单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        self.logger = logger
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 加载配置
        self._config = {
            "CLIENT_ID": None,
            "DEVICE_ID": None,
            "MQTT_INFO": None,
            "NETWORK": XIAOZHI_CONFIG,
        }

        self._initialize_client_id()
        self._initialize_device_id()
        self._initialize_mqtt_info()

    def get_client_id(self) -> str:
        """获取客户端ID"""
        return self._config["CLIENT_ID"]

    def get_device_id(self) -> Optional[str]:
        """获取设备ID"""
        return self._config.get("DEVICE_ID")

    def get_network_config(self) -> dict:
        """获取网络配置"""
        return self._config["NETWORK"]

    def get_config(self, path: str, default: Any = None) -> Any:
        """
        通过路径获取配置值
        """
        try:
            value = self._config
            for key in path.split("."):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_config(self, path: str, value: Any) -> bool:
        """
        更新特定配置项
        """
        try:
            current = self._config
            *parts, last = path.split(".")
            for part in parts:
                current = current.setdefault(part, {})
            current[last] = value
            return True
        except Exception as e:
            logger.error(f"Error updating config {path}: {e}")
            return False

    @classmethod
    def instance(cls):
        """获取配置管理器实例（线程安全）"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def get_mac_address(self):
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return ":".join([mac[i : i + 2] for i in range(0, 12, 2)])

    def generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _initialize_client_id(self):
        """确保存在客户端ID"""
        if not self._config["CLIENT_ID"]:
            client_id = self.generate_uuid()
            success = self.update_config("CLIENT_ID", client_id)
            if success:
                logger.info(f"Generated new CLIENT_ID: {client_id}")
            else:
                logger.error("Failed to save new CLIENT_ID")

    def _initialize_device_id(self):
        """确保存在设备ID"""
        if not self._config["DEVICE_ID"]:
            try:
                device_hash = self.get_mac_address()
                success = self.update_config("DEVICE_ID", device_hash)
                if success:
                    logger.info(f"Generated new DEVICE_ID: {device_hash}")
                else:
                    logger.error("Failed to save new DEVICE_ID")
            except Exception as e:
                logger.error(f"Error generating DEVICE_ID: {e}")

    def refresh_mqtt_info(self):
        """刷新 MQTT 信息"""
        if not self._config["MQTT_INFO"]:
            self._initialize_mqtt_info()

    def _initialize_mqtt_info(self):
        try:
            mqtt_info = self._get_ota_version()
            if mqtt_info:
                self.update_config("MQTT_INFO", mqtt_info)
                self.logger.info("MQTT信息已成功更新")
                return mqtt_info
            else:
                self.logger.warning("获取MQTT信息失败，使用已保存的配置")
                return self.get_config("MQTT_INFO")
        except Exception as e:
            self.logger.error(f"初始化MQTT信息失败: {e}")
            return self.get_config("MQTT_INFO")

    def _get_ota_version(self):
        """获取OTA服务器的MQTT信息"""
        MAC_ADDR = self.get_device_id()
        OTA_URL = self.get_config("NETWORK.OTA_URL")
        headers = {
            "Activation-Version": "1",
            "Device-Id": MAC_ADDR,
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN",
        }

        # 构建设备信息 payload
        payload = {
            "mac_address": MAC_ADDR,
            "board": {
                "type": "lc-esp32-s3",
                "name": "立创ESP32-S3开发板",
                "features": ["wifi", "ble", "psram", "octal_flash"],
                "ip": self.get_local_ip(),
                "mac": MAC_ADDR,
            },
            "application": {
                "name": "xiaozhi",
                "version": "1.6.0",
                "compile_time": "2025-4-16T12:00:00Z",
                "idf_version": "v5.3.2",
            },
            "psram_size": 8388608,  # 8MB PSRAM
            "minimum_free_heap_size": 7265024,  # 最小可用堆内存
            "chip_model_name": "esp32s3",  # 芯片型号
            "chip_info": {
                "model": 9,  # ESP32-S3
                "cores": 2,
                "revision": 0,  # 芯片版本修订
                "features": 20,  # WiFi + BLE + PSRAM
            },
            "partition_table": [],
            "ota": {"label": "factory"},
        }

        try:
            # 发送请求到OTA服务器
            response = requests.post(
                OTA_URL,
                headers=headers,
                json=payload,
                timeout=10,
            )

            # 检查HTTP状态码
            if response.status_code != 200:
                self.logger.error(f"OTA服务器错误: HTTP {response.status_code}")
                raise ValueError(f"OTA服务器返回错误状态码: {response.status_code}")

            # 解析JSON数据
            response_data = response.json()

            self.logger.debug(
                f"OTA服务器返回数据: {json.dumps(response_data, indent=4, ensure_ascii=False)}"
            )
            if "mqtt" in response_data:
                self.logger.info("MQTT服务器信息已更新")
                return response_data["mqtt"]
            else:
                self.logger.error("OTA服务器返回的数据无效: MQTT信息缺失")
                raise ValueError("OTA服务器返回的数据无效，请检查服务器状态或MAC地址！")

        except requests.Timeout:
            self.logger.error("OTA请求超时，请检查网络或服务器状态")
            raise ValueError("OTA请求超时！请稍后重试。")

        except requests.RequestException as e:
            self.logger.error(f"OTA请求失败: {e}")
            raise ValueError("无法连接到OTA服务器，请检查网络连接！")
