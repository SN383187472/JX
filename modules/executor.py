"""
命令执行器 - 远程命令执行模块
"""
import paramiko
import asyncio
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger("executor")


@dataclass
class CommandResult:
    """命令执行结果"""
    command: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    execution_time: float  # 秒


class CommandExecutor:
    """
    命令执行器
    
    支持通过SSH远程执行命令，用于基线检查
    """
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = None,
        password: str = None,
        timeout: int = 30
    ):
        """
        初始化执行器
        
        Args:
            host: 目标主机
            port: SSH端口
            username: 用户名
            password: 密码
            timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> bool:
        """
        建立SSH连接
        
        Returns:
            连接是否成功
        """
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            logger.info(f"SSH连接成功: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"SSH连接失败: {self.host}:{self.port} - {str(e)}")
            return False
    
    def disconnect(self):
        """断开SSH连接"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info(f"SSH连接已断开: {self.host}")
    
    def execute(self, command: str, timeout: int = None) -> CommandResult:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒），None使用默认值
        
        Returns:
            CommandResult 对象
        """
        if not self._client:
            return CommandResult(
                command=command,
                stdout="",
                stderr="SSH连接未建立",
                exit_code=-1,
                success=False,
                execution_time=0
            )
        
        import time
        start_time = time.time()
        
        try:
            stdin, stdout, stderr = self._client.exec_command(
                command,
                timeout=timeout or self.timeout
            )
            
            stdout_str = stdout.read().decode('utf-8', errors='ignore').strip()
            stderr_str = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_code = stdout.channel.recv_exit_status()
            
            execution_time = time.time() - start_time
            
            return CommandResult(
                command=command,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=exit_code,
                success=(exit_code == 0),
                execution_time=execution_time
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"命令执行失败: {command} - {str(e)}")
            return CommandResult(
                command=command,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False,
                execution_time=execution_time
            )
    
    def execute_batch(self, commands: list) -> list:
        """
        批量执行命令
        
        Args:
            commands: 命令列表
        
        Returns:
            CommandResult 列表
        """
        results = []
        for cmd in commands:
            result = self.execute(cmd)
            results.append(result)
        return results
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 异步执行器（用于FastAPI异步调用）
class AsyncCommandExecutor(CommandExecutor):
    """异步命令执行器"""
    
    async def connect_async(self) -> bool:
        """异步建立连接"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connect)
    
    async def execute_async(self, command: str, timeout: int = None) -> CommandResult:
        """异步执行命令"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, command, timeout)
    
    async def disconnect_async(self):
        """异步断开连接"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.disconnect)
