"""
Windows系统扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger("scanner.windows")


class WindowsScanner(BaseScanner):
    """
    Windows操作系统基线扫描器
    
    支持通过WinRM或SSH远程检查Windows系统安全配置
    """
    
    scanner_type = "windows"
    DEFAULT_SSH_PORT = 22
    DEFAULT_WINRM_PORT = 5985
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        use_winrm: bool = False,
        **kwargs
    ):
        super().__init__(
            host=host,
            port=port or (self.DEFAULT_WINRM_PORT if use_winrm else self.DEFAULT_SSH_PORT),
            username=username,
            password=password,
            **kwargs
        )
        self.use_winrm = use_winrm
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "windows"
    
    async def connect(self) -> bool:
        """建立连接"""
        try:
            self._executor = AsyncCommandExecutor(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=30
            )
            self._connected = await self._executor.connect_async()
            
            if self._connected:
                self.logger.info(f"Windows系统连接成功: {self.host}:{self.port}")
            else:
                self.logger.error(f"Windows系统连接失败: {self.host}:{self.port}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"Windows系统连接已断开: {self.host}")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """执行命令"""
        if not self._connected:
            return {
                "success": False,
                "stdout": "",
                "stderr": "未连接",
                "exit_code": -1
            }
        
        result = await self._executor.execute_async(command)
        
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time
        }
    
    async def check_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """检查单条规则"""
        rule_id = rule.get("id", "unknown")
        rule_name = rule.get("name", "未知规则")
        command = rule.get("command", "")
        expected = rule.get("expected", "")
        check_type = rule.get("check_type", "contains")
        description = rule.get("description", "")
        severity = rule.get("severity", "medium")
        category = rule.get("category", "general")
        
        cmd_result = await self.execute_command(command)
        
        output = cmd_result.get("stdout", "")
        stderr = cmd_result.get("stderr", "")
        
        if stderr and not output:
            output = f"[ERROR] {stderr}"
        
        passed, analysis = self.analyze_result(output, expected, check_type)
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "description": description,
            "status": "pass" if passed else "fail",
            "command": command,
            "output": output[:1000],
            "expected": expected,
            "actual": output[:200],
            "analysis": analysis,
            "severity": severity,
            "category": category
        }
    
    # Windows特有检查方法
    async def check_windows_version(self) -> Dict[str, Any]:
        """检查Windows版本"""
        result = await self.execute_command("ver")
        return result
    
    async def check_windows_update(self) -> Dict[str, Any]:
        """检查Windows更新状态"""
        result = await self.execute_command("wmic qfe list brief")
        return result
    
    async def check_windows_firewall(self) -> Dict[str, Any]:
        """检查Windows防火墙"""
        result = await self.execute_command("netsh advfirewall show allprofiles state")
        return result
