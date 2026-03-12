"""
达梦数据库扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger("scanner.dameng")


class DamengScanner(BaseScanner):
    """
    达梦数据库基线扫描器
    
    支持通过SSH远程检查达梦数据库安全配置
    注意：需要数据库客户端工具（disql）或直接查询数据库
    """
    
    scanner_type = "dameng"
    
    # 达梦默认端口
    DEFAULT_DM_PORT = 5236
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        db_port: int = None,
        db_user: str = None,
        db_password: str = None,
        **kwargs
    ):
        super().__init__(
            host=host,
            port=port or 22,  # SSH端口
            username=username,
            password=password,
            **kwargs
        )
        
        # 数据库连接信息
        self.db_port = db_port or self.DEFAULT_DM_PORT
        self.db_user = db_user or username
        self.db_password = db_password or password
        
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "dameng"
    
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
                self.logger.info(f"达梦数据库服务器连接成功: {self.host}")
            else:
                self.logger.error(f"达梦数据库服务器连接失败: {self.host}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"达梦数据库服务器连接已断开: {self.host}")
    
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
    
    async def execute_sql(self, sql: str, disql_path: str = "disql") -> Dict[str, Any]:
        """
        执行SQL命令
        
        Args:
            sql: SQL语句
            disql_path: disql工具路径
        
        Returns:
            执行结果
        """
        # 构造disql命令
        # 格式: disql dbuser/dbpassword@host:port -e "SQL语句"
        cmd = f'{disql_path} {self.db_user}/"{self.db_password}"@{self.host}:{self.db_port} -e "{sql}"'
        
        result = await self.execute_command(cmd)
        return result
    
    async def check_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """检查单条规则"""
        rule_id = rule.get("id", "unknown")
        rule_name = rule.get("name", "未知规则")
        command = rule.get("command", "")
        sql = rule.get("sql", "")
        expected = rule.get("expected", "")
        check_type = rule.get("check_type", "contains")
        description = rule.get("description", "")
        severity = rule.get("severity", "medium")
        category = rule.get("category", "general")
        
        # 优先执行SQL，如果没有则执行命令
        if sql:
            cmd_result = await self.execute_sql(sql)
        else:
            cmd_result = await self.execute_command(command)
        
        output = cmd_result.get("stdout", "")
        stderr = cmd_result.get("stderr", "")
        
        if stderr and not output:
            output = f"[ERROR] {stderr}"
        
        # 分析结果
        passed, analysis = self.analyze_result(output, expected, check_type)
        
        return {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "description": description,
            "status": "pass" if passed else "fail",
            "command": sql if sql else command,
            "output": output[:1000],
            "expected": expected,
            "actual": output[:200],
            "analysis": analysis,
            "severity": severity,
            "category": category
        }
    
    # ============ 预定义检查方法 ============
    
    async def check_dm_version(self) -> Dict[str, Any]:
        """检查达梦版本"""
        result = await self.execute_command("disql -v")
        return result
    
    async def check_dm_status(self) -> Dict[str, Any]:
        """检查达梦服务状态"""
        result = await self.execute_command("systemctl status DmService* 2>/dev/null || ps -ef | grep dmserver")
        return result
    
    async def check_user_accounts(self) -> Dict[str, Any]:
        """检查数据库用户"""
        sql = "SELECT USERNAME, ACCOUNT_STATUS FROM DBA_USERS;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_password_policy(self) -> Dict[str, Any]:
        """检查密码策略"""
        sql = "SELECT * FROM V$PARAMETER WHERE NAME LIKE '%PWD%';"
        result = await self.execute_sql(sql)
        return result
    
    async def check_privileges(self) -> Dict[str, Any]:
        """检查用户权限"""
        sql = "SELECT GRANTEE, PRIVILEGE FROM DBA_SYS_PRIVS;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_audit_status(self) -> Dict[str, Any]:
        """检查审计状态"""
        sql = "SELECT * FROM V$PARAMETER WHERE NAME = 'AUDIT_FILE_PATH' OR NAME = 'AUDIT_MODE';"
        result = await self.execute_sql(sql)
        return result
