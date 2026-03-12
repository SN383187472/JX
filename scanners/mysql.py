"""
MySQL数据库扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger("scanner.mysql")


class MySQLScanner(BaseScanner):
    """
    MySQL数据库基线扫描器
    
    支持通过SSH远程检查MySQL数据库安全配置
    可通过MySQL客户端工具执行SQL查询
    """
    
    scanner_type = "mysql"
    
    # MySQL默认端口
    DEFAULT_MYSQL_PORT = 3306
    
    def __init__(
        self,
        host: str,
        port: int = None,
        username: str = None,
        password: str = None,
        db_port: int = None,
        db_user: str = None,
        db_password: str = None,
        db_name: str = None,
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
        self.db_port = db_port or self.DEFAULT_MYSQL_PORT
        self.db_user = db_user or username or "root"
        self.db_password = db_password or password
        self.db_name = db_name or "mysql"
        
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "mysql"
    
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
                self.logger.info(f"MySQL服务器连接成功: {self.host}")
            else:
                self.logger.error(f"MySQL服务器连接失败: {self.host}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"MySQL服务器连接已断开: {self.host}")
    
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
    
    async def execute_sql(self, sql: str, mysql_path: str = "mysql") -> Dict[str, Any]:
        """
        执行SQL命令
        
        Args:
            sql: SQL语句
            mysql_path: mysql客户端工具路径
        
        Returns:
            执行结果
        """
        # 构造mysql命令
        # 格式: mysql -u user -p'password' -h host -P port -e "SQL语句"
        # 使用 -t 获取表格格式输出
        cmd = f'{mysql_path} -u {self.db_user} -p\'{self.db_password}\' -h {self.host} -P {self.db_port} -t -e "{sql}" 2>/dev/null'
        
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
    
    async def check_mysql_version(self) -> Dict[str, Any]:
        """检查MySQL版本"""
        result = await self.execute_sql("SELECT VERSION();")
        return result
    
    async def check_mysql_status(self) -> Dict[str, Any]:
        """检查MySQL服务状态"""
        result = await self.execute_command("systemctl is-active mysqld 2>/dev/null || systemctl is-active mysql 2>/dev/null || ps -ef | grep mysqld | grep -v grep")
        return result
    
    async def check_user_accounts(self) -> Dict[str, Any]:
        """检查数据库用户"""
        sql = "SELECT user,host FROM mysql.user;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_empty_password_users(self) -> Dict[str, Any]:
        """检查空密码用户"""
        sql = "SELECT user,host FROM mysql.user WHERE authentication_string='' OR password IS NULL;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_anonymous_users(self) -> Dict[str, Any]:
        """检查匿名用户"""
        sql = "SELECT user,host FROM mysql.user WHERE user='';"
        result = await self.execute_sql(sql)
        return result
    
    async def check_privileges(self) -> Dict[str, Any]:
        """检查用户权限"""
        sql = "SELECT user,host,Super_priv,Grant_priv FROM mysql.user;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_variables(self, pattern: str = "%") -> Dict[str, Any]:
        """检查系统变量"""
        sql = f"SHOW VARIABLES LIKE '{pattern}';"
        result = await self.execute_sql(sql)
        return result
    
    async def check_audit_status(self) -> Dict[str, Any]:
        """检查审计状态"""
        sql = "SHOW VARIABLES LIKE 'general_log';"
        result = await self.execute_sql(sql)
        return result
    
    async def check_ssl_status(self) -> Dict[str, Any]:
        """检查SSL状态"""
        sql = "SHOW VARIABLES LIKE 'have_ssl';"
        result = await self.execute_sql(sql)
        return result
    
    async def check_databases(self) -> Dict[str, Any]:
        """获取数据库列表"""
        sql = "SHOW DATABASES;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_database_sizes(self) -> Dict[str, Any]:
        """获取数据库大小"""
        sql = "SELECT table_schema, ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb FROM information_schema.tables GROUP BY table_schema;"
        result = await self.execute_sql(sql)
        return result
