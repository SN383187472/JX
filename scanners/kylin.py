"""
麒麟操作系统扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner, CheckResult
from modules.executor import CommandExecutor, AsyncCommandExecutor

logger = logging.getLogger("scanner.kylin")


class KylinScanner(BaseScanner):
    """
    麒麟操作系统基线扫描器
    
    支持通过SSH远程检查麒麟系统安全配置
    """
    
    scanner_type = "kylin"
    
    # 默认SSH端口
    DEFAULT_SSH_PORT = 22
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        **kwargs
    ):
        super().__init__(
            host=host,
            port=port or self.DEFAULT_SSH_PORT,
            username=username,
            password=password,
            **kwargs
        )
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "kylin"
    
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
                self.logger.info(f"麒麟系统连接成功: {self.host}:{self.port}")
            else:
                self.logger.error(f"麒麟系统连接失败: {self.host}:{self.port}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"麒麟系统连接已断开: {self.host}")
    
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
        
        # 执行命令
        cmd_result = await self.execute_command(command)
        
        output = cmd_result.get("stdout", "")
        stderr = cmd_result.get("stderr", "")
        
        # 如果有错误输出，也包含在分析中
        if stderr and not output:
            output = f"[ERROR] {stderr}"
        
        # 分析结果
        passed, analysis = self.analyze_result(output, expected, check_type)
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "description": description,
            "status": "pass" if passed else "fail",
            "command": command,
            "output": output[:1000],  # 限制输出长度
            "expected": expected,
            "actual": output[:200],
            "analysis": analysis,
            "severity": severity,
            "category": category
        }
    
    # ============ 预定义检查方法 ============
    
    async def check_password_policy(self) -> Dict[str, Any]:
        """检查密码策略"""
        result = await self.execute_command(
            "grep -E '^PASS_MAX_DAYS|^PASS_MIN_DAYS|^PASS_WARN_AGE' /etc/login.defs"
        )
        return result
    
    async def check_login_config(self) -> Dict[str, Any]:
        """检查登录配置"""
        result = await self.execute_command(
            "cat /etc/ssh/sshd_config | grep -E '^PermitRootLogin|^PermitEmptyPasswords|^PasswordAuthentication'"
        )
        return result
    
    async def check_firewall_status(self) -> Dict[str, Any]:
        """检查防火墙状态"""
        result = await self.execute_command("systemctl status firewalld 2>/dev/null || iptables -L -n")
        return result
    
    async def check_open_ports(self) -> Dict[str, Any]:
        """检查开放端口"""
        result = await self.execute_command("netstat -tuln | grep LISTEN")
        return result
    
    async def check_users(self) -> Dict[str, Any]:
        """检查用户账户"""
        result = await self.execute_command(
            "cat /etc/passwd | grep -v nologin | grep -v false"
        )
        return result
    
    async def check_services(self) -> Dict[str, Any]:
        """检查服务状态"""
        result = await self.execute_command("systemctl list-units --type=service --state=running")
        return result
