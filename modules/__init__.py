"""
模块基类
"""
from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional
from datetime import datetime


class BaseModule(ABC):
    """
    模块基类 - 所有功能模块的父类
    
    提供统一的接口和通用功能：
    - 日志记录
    - 配置管理
    - 错误处理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模块
        
        Args:
            config: 模块配置字典
        """
        self.config = config or {}
        self.module_name = self.__class__.__name__
        self.logger = logging.getLogger(f"module.{self.module_name}")
        self._initialized = False
        self._created_at = datetime.now()
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化模块（子类必须实现）
        
        Returns:
            初始化是否成功
        """
        pass
    
    def is_initialized(self) -> bool:
        """检查模块是否已初始化"""
        return self._initialized
    
    def get_info(self) -> Dict[str, Any]:
        """获取模块信息"""
        return {
            "name": self.module_name,
            "initialized": self._initialized,
            "created_at": self._created_at.isoformat()
        }
    
    # 日志方法
    def log_debug(self, message: str):
        self.logger.debug(f"[{self.module_name}] {message}")
    
    def log_info(self, message: str):
        self.logger.info(f"[{self.module_name}] {message}")
    
    def log_warning(self, message: str):
        self.logger.warning(f"[{self.module_name}] {message}")
    
    def log_error(self, message: str):
        self.logger.error(f"[{self.module_name}] {message}")
    
    # 配置方法
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
