"""
Linux通用扫描器 - 支持CentOS/Ubuntu等
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger("scanner.linux")


class LinuxScanner(BaseScanner):
    """
    Linux操作系统基线扫描器
    
    支持CentOS、Ubuntu等常见Linux发行版
    """
    
    scanner_type = "linux"
    DEFAULT_SSH_PORT = 22
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        distro: str = "auto",  # auto, centos, ubuntu, debian
        **kwargs
    ):
        super().__init__(
            host=host,
            port=port or self.DEFAULT_SSH_PORT,
            username=username,
            password=password,
            **kwargs
        )
        self.distro = distro
        self._executor: AsyncCommandExecutor = None
        self._detected_distro = None
    
    @property
    def scanner_type(self) -> str:
        return "linux"
    
    async def connect(self) -> bool:
        """建立SSH连接"""
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
                self.logger.info(f"Linux系统连接成功: {self.host}:{self.port}")
                # 自动检测发行版
                if self.distro == "auto":
                    await self._detect_distro()
            else:
                self.logger.error(f"Linux系统连接失败: {self.host}:{self.port}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def _detect_distro(self):
        """检测Linux发行版"""
        result = await self.execute_command("cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || cat /etc/debian_version 2>/dev/null")
        output = result.get("stdout", "").lower()
        
        if "centos" in output or "rhel" in output or "red hat" in output:
            self._detected_distro = "centos"
        elif "ubuntu" in output:
            self._detected_distro = "ubuntu"
        elif "debian" in output:
            self._detected_distro = "debian"
        elif "kylin" in output:
            self._detected_distro = "kylin"
        else:
            self._detected_distro = "linux"
        
        self.logger.info(f"检测到发行版: {self._detected_distro}")
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"Linux系统连接已断开: {self.host}")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """执行Shell命令"""
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
        
        # 支持发行版特定命令
        distro_command = rule.get(f"command_{self._detected_distro}", command)
        
        cmd_result = await self.execute_command(distro_command)
        
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
            "command": distro_command,
            "output": output[:1000],
            "expected": expected,
            "actual": output[:200],
            "analysis": analysis,
            "severity": severity,
            "category": category
        }
    
    # Linux通用检查方法
    async def check_kernel_version(self) -> Dict[str, Any]:
        """检查内核版本"""
        result = await self.execute_command("uname -r")
        return result
    
    async def check_package_updates(self) -> Dict[str, Any]:
        """检查可用更新"""
        if self._detected_distro in ["ubuntu", "debian"]:
            result = await self.execute_command("apt list --upgradable 2>/dev/null | head -20")
        else:
            result = await self.execute_command("yum check-update 2>/dev/null | head -20")
        return result
