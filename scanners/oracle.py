"""
Oracle数据库扫描器
"""
from typing import Dict, Any, List
import asyncio
import re
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger("scanner.oracle")


class OracleScanner(BaseScanner):
    """
    Oracle数据库基线扫描器
    
    支持通过SSH远程检查Oracle数据库安全配置
    可通过sqlplus工具执行SQL查询
    """
    
    scanner_type = "oracle"
    
    # Oracle默认端口
    DEFAULT_ORACLE_PORT = 1521
    
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
        oracle_sid: str = None,
        oracle_home: str = None,
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
        self.db_port = db_port or self.DEFAULT_ORACLE_PORT
        self.db_user = db_user or username or "system"
        self.db_password = db_password or password
        self.db_name = db_name or "ORCL"
        self.oracle_sid = oracle_sid or "ORCL"
        self.oracle_home = oracle_home
        
        self._executor: AsyncCommandExecutor = None
    
    @property
    def scanner_type(self) -> str:
        return "oracle"
    
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
                self.logger.info(f"Oracle服务器连接成功: {self.host}")
                # 获取Oracle环境变量
                if not self.oracle_home:
                    await self._detect_oracle_home()
            else:
                self.logger.error(f"Oracle服务器连接失败: {self.host}")
            
            return self._connected
        except Exception as e:
            self.logger.error(f"连接异常: {str(e)}")
            return False
    
    async def _detect_oracle_home(self):
        """检测Oracle Home目录"""
        result = await self.execute_command("echo $ORACLE_HOME")
        oracle_home = result.get("stdout", "").strip()
        if oracle_home:
            self.oracle_home = oracle_home
            self.logger.info(f"检测到ORACLE_HOME: {oracle_home}")
    
    async def disconnect(self):
        """断开SSH连接"""
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f"Oracle服务器连接已断开: {self.host}")
    
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
    
    async def execute_sql(self, sql: str, sqlplus_path: str = None) -> Dict[str, Any]:
        """
        执行SQL命令
        
        Args:
            sql: SQL语句
            sqlplus_path: sqlplus工具路径
        
        Returns:
            执行结果
        """
        if not sqlplus_path:
            if self.oracle_home:
                sqlplus_path = f"{self.oracle_home}/bin/sqlplus"
            else:
                sqlplus_path = "sqlplus"
        
        # 构造sqlplus命令
        # 格式: sqlplus user/password@host:port/service @- <<EOF ... EOF
        # 或使用SID: sqlplus user/password@host:port/sid
        connection_string = f"{self.db_user}/{self.db_password}@{self.host}:{self.db_port}/{self.oracle_sid}"
        
        # 转义SQL中的引号
        escaped_sql = sql.replace('"', '\\"')
        
        # 使用echo传递SQL
        cmd = f'echo "{escaped_sql}" | {sqlplus_path} -S {connection_string} 2>/dev/null'
        
        result = await self.execute_command(cmd)
        return result
    
    async def execute_sql_script(self, sql: str) -> Dict[str, Any]:
        """
        执行SQL脚本（支持多行SQL）
        
        Args:
            sql: SQL语句
        
        Returns:
            执行结果
        """
        connection_string = f"{self.db_user}/{self.db_password}@{self.host}:{self.db_port}/{self.oracle_sid}"
        
        sqlplus_path = "sqlplus"
        if self.oracle_home:
            sqlplus_path = f"{self.oracle_home}/bin/sqlplus"
        
        # 使用here document
        cmd = f'''{sqlplus_path} -S {connection_string} << 'EOF'
SET PAGESIZE 1000
SET LINESIZE 200
SET FEEDBACK OFF
SET HEADING ON
{sql}
EXIT
EOF
'''
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
            # 对于包含SHOW PARAMETER的语句，需要特殊处理
            if "SHOW PARAMETER" in sql.upper() or "SHOW VARIABLES" in sql.upper():
                cmd_result = await self.execute_sql(sql)
            else:
                cmd_result = await self.execute_sql_script(sql)
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
    
    async def check_oracle_version(self) -> Dict[str, Any]:
        """检查Oracle版本"""
        sql = "SELECT * FROM v$version WHERE banner LIKE 'Oracle%';"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_oracle_status(self) -> Dict[str, Any]:
        """检查Oracle服务状态"""
        result = await self.execute_command("ps -ef | grep ora_pmon | grep -v grep")
        return result
    
    async def check_listener_status(self) -> Dict[str, Any]:
        """检查监听状态"""
        result = await self.execute_command("lsnrctl status 2>/dev/null | grep STATUS || ps -ef | grep tnslsnr | grep -v grep")
        return result
    
    async def check_user_accounts(self) -> Dict[str, Any]:
        """检查数据库用户"""
        sql = "SELECT username, account_status, created FROM dba_users ORDER BY created DESC;"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_default_accounts(self) -> Dict[str, Any]:
        """检查默认账户"""
        sql = "SELECT username, account_status FROM dba_users WHERE username IN ('SCOTT','HR','OE','PM','IX','SH','BI') AND account_status='OPEN';"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_password_policy(self) -> Dict[str, Any]:
        """检查密码策略"""
        sql = "SELECT resource_name, limit FROM dba_profiles WHERE profile='DEFAULT' AND resource_type='PASSWORD';"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_dba_users(self) -> Dict[str, Any]:
        """检查DBA权限用户"""
        sql = "SELECT grantee FROM dba_role_privs WHERE granted_role='DBA';"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_audit_status(self) -> Dict[str, Any]:
        """检查审计状态"""
        sql = "SHOW PARAMETER audit_trail;"
        result = await self.execute_sql(sql)
        return result
    
    async def check_archive_mode(self) -> Dict[str, Any]:
        """检查归档模式"""
        sql = "SELECT log_mode FROM v$database;"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_control_files(self) -> Dict[str, Any]:
        """检查控制文件"""
        sql = "SELECT name FROM v$controlfile;"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_redo_logs(self) -> Dict[str, Any]:
        """检查重做日志"""
        sql = "SELECT group#, status, member FROM v$logfile;"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_tablespaces(self) -> Dict[str, Any]:
        """检查表空间"""
        sql = "SELECT tablespace_name, bytes/1024/1024 AS size_mb FROM dba_data_files ORDER BY tablespace_name;"
        result = await self.execute_sql_script(sql)
        return result
    
    async def check_rman_backups(self) -> Dict[str, Any]:
        """检查RMAN备份"""
        sql = "SELECT start_time, status, output_device_type FROM v$rman_status WHERE start_time > SYSDATE-7 ORDER BY start_time DESC;"
        result = await self.execute_sql_script(sql)
        return result
