"""
Apache HTTP Server 扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner, CheckResult
from modules.executor import CommandExecutor, AsyncCommandExecutor

logger = logging.getLogger("scanner.apache")


class ApacheScanner(BaseScanner):
    """
    Apache HTTP Server 基线扫描器
    
    支持通过SSH远程检查Apache安全配置
    """
    
    scanner_type = "apache"
    
    # 默认HTTP端口
    DEFAULT_PORT = 80
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        ssh_port: int = 22,
        config_path: str = None,
        **kwargs
    ):
        super().__init__(
            host=host,
            port=port or self.DEFAULT_PORT,
            username=username,
            password=password,
            **kwargs
        )
        self.ssh_port = ssh_port
        self.config_path = config_path
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "apache"
    
    async def connect(self) -> bool:
        """建立SSH连接"""
        try:
            self._executor = AsyncCommandExecutor(
                host=self.host,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=30
            )
            self._connected = await self._executor.connect_async()
            
            if self._connected:
                self.logger.info(f"Apache服务器连接成功: {self.host}:{self.ssh_port}")
                # 检测Apache是否安装
                await self._detect_apache()
            else:
                self.logger.error(f"Apache服务器连接失败: {self.host}:{self.ssh_port}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def _detect_apache(self):
        """检测Apache安装路径和版本"""
        # 检测Apache版本
        result = await self.execute_command("httpd -v 2>/dev/null || apache2 -v 2>/dev/null")
        if result.get("success"):
            self.version_info = result.get("stdout", "")
            self.logger.info(f"Apache版本: {self.version_info}")
        
        # 检测配置文件路径
        config_result = await self.execute_command(
            "find /etc/httpd /etc/apache2 -name 'httpd.conf' -o -name 'apache2.conf' 2>/dev/null | head -5"
        )
        if config_result.get("success") and config_result.get("stdout"):
            self.config_paths = config_result.get("stdout", "").strip().split("\n")
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"Apache服务器连接已断开: {self.host}")
    
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
        remediation = rule.get("remediation", "")
        
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
            "output": output[:1000],
            "expected": expected,
            "actual": output[:200],
            "analysis": analysis,
            "severity": severity,
            "category": category,
            "remediation": remediation
        }
    
    # ============ 预定义检查方法 ============
    
    async def check_version(self) -> Dict[str, Any]:
        """检查Apache版本"""
        return await self.execute_command("httpd -v 2>/dev/null || apache2 -v 2>/dev/null")
    
    async def check_loaded_modules(self) -> Dict[str, Any]:
        """检查已加载模块"""
        return await self.execute_command("apachectl -M 2>/dev/null || apache2ctl -M 2>/dev/null")
    
    async def check_ssl_config(self) -> Dict[str, Any]:
        """检查SSL配置"""
        return await self.execute_command(
            "grep -rE 'SSLProtocol|SSLCipherSuite|SSLCertificateFile' "
            "/etc/httpd/ /etc/apache2/ 2>/dev/null | grep -v '#'"
        )
    
    async def check_security_headers(self) -> Dict[str, Any]:
        """检查安全响应头"""
        return await self.execute_command(
            "grep -rE 'Header.*set|X-Frame-Options|X-Content-Type-Options|X-XSS-Protection' "
            "/etc/httpd/ /etc/apache2/ 2>/dev/null | grep -v '#'"
        )
    
    async def check_logging(self) -> Dict[str, Any]:
        """检查日志配置"""
        return await self.execute_command(
            "grep -rE 'CustomLog|ErrorLog|LogLevel' "
            "/etc/httpd/ /etc/apache2/ 2>/dev/null | grep -v '#' | head -10"
        )
