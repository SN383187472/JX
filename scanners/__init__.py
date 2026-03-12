"""
扫描器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging


@dataclass
class CheckResult:
    """单条检查结果"""
    rule_id: str
    rule_name: str
    description: str
    status: str  # pass, fail, error
    command: str
    output: str
    expected: str
    actual: str
    analysis: str
    severity: str  # high, medium, low
    category: str


class BaseScanner(ABC):
    """
    扫描器基类
    
    所有扫描器的父类，定义统一接口
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        **kwargs
    ):
        """
        初始化扫描器
        
        Args:
            host: 目标主机
            port: 端口
            username: 用户名
            password: 密码
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.config = kwargs
        
        self.logger = logging.getLogger(f"scanner.{self.__class__.__name__}")
        self._executor = None
        self._connected = False
    
    @property
    @abstractmethod
    def scanner_type(self) -> str:
        """扫描器类型标识"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """执行命令"""
        pass
    
    async def scan(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行扫描
        
        Args:
            rules: 规则列表
        
        Returns:
            扫描结果列表
        """
        results = []
        
        # 建立连接
        if not await self.connect():
            return [self._create_error_result(rule, "连接失败") for rule in rules]
        
        try:
            for rule in rules:
                try:
                    result = await self.check_rule(rule)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"规则检查失败: {rule.get('id')} - {str(e)}")
                    results.append(self._create_error_result(rule, str(e)))
        finally:
            await self.disconnect()
        
        return results
    
    @abstractmethod
    async def check_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查单条规则
        
        Args:
            rule: 规则定义
        
        Returns:
            检查结果
        """
        pass
    
    def _create_error_result(self, rule: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "rule_id": rule.get("id", "unknown"),
            "rule_name": rule.get("name", "未知规则"),
            "description": rule.get("description", ""),
            "status": "error",
            "command": rule.get("command", ""),
            "output": "",
            "expected": rule.get("expected", ""),
            "actual": "",
            "analysis": f"检查失败: {error_msg}",
            "severity": rule.get("severity", "medium"),
            "category": rule.get("category", "general")
        }
    
    def analyze_result(
        self,
        output: str,
        expected: str,
        check_type: str = "contains"
    ) -> tuple:
        """
        分析检查结果
        
        Args:
            output: 命令输出
            expected: 期望值
            check_type: 检查类型 (contains, equals, regex, not_empty)
        
        Returns:
            (是否通过, 分析说明)
        """
        import re
        
        if check_type == "contains":
            passed = expected in output
            analysis = f"期望包含 '{expected}'，{'符合' if passed else '不符合'}"
        elif check_type == "equals":
            passed = output.strip() == expected.strip()
            analysis = f"期望等于 '{expected}'，{'符合' if passed else '不符合'}"
        elif check_type == "regex":
            passed = bool(re.search(expected, output))
            analysis = f"正则匹配 '{expected}'，{'匹配' if passed else '不匹配'}"
        elif check_type == "not_empty":
            passed = bool(output.strip())
            analysis = f"期望非空，{'符合' if passed else '不符合'}"
        elif check_type == "not_contains":
            passed = expected not in output
            analysis = f"期望不包含 '{expected}'，{'符合' if passed else '不符合'}"
        else:
            passed = False
            analysis = f"未知的检查类型: {check_type}"
        
        return passed, analysis
