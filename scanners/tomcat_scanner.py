"""
Tomcat scanner
"""
from typing import Dict, Any, List
import asyncio
import logging

from . import BaseScanner
from modules.executor import AsyncCommandExecutor

logger = logging.getLogger('scanner.tomcat')


class TomcatScanner(BaseScanner):
    """Tomcat基线扫描器"""
    
    scanner_type = 'tomcat'
    DEFAULT_SSH_PORT = 22
    
    def __init__(self, host: str, port: int = None, ssh_port: int = 22,
                 username: str = None, password: str = None, **kwargs):
        super().__init__(
            host=host,
            port=port or 8080,
            username=username,
            password=password,
            **kwargs
        )
        self.ssh_port = ssh_port
        self._executor = None
    
    @property
    def scanner_type(self) -> str:
        return 'tomcat'
    
    async def connect(self) -> bool:
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
                self.logger.info(f'Tomcat connect success: {self.host}:{self.ssh_port}')
            else:
                self.logger.error(f'Tomcat connect failed: {self.host}:{self.ssh_port}')
            
            return self._connected
        except Exception as e:
            self.logger.error(f'Connection error: {str(e)}')
            return False
    
    async def disconnect(self):
        if self._executor:
            await self._executor.disconnect_async()
            self._connected = False
            self.logger.info(f'Tomcat disconnected: {self.host}')
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        if not self._connected:
            return {'success': False, 'stdout': '', 'stderr': 'Not connected', 'exit_code': -1}
        
        result = await self._executor.execute_async(command)
        
        return {
            'success': result.success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.exit_code,
            'execution_time': result.execution_time
        }
    
    async def check_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        rule_id = rule.get('id', 'unknown')
        rule_name = rule.get('name', 'Unknown Rule')
        command = rule.get('command', '')
        expected = rule.get('expected', '')
        check_type = rule.get('check_type', 'contains')
        description = rule.get('description', '')
        severity = rule.get('severity', 'medium')
        category = rule.get('category', 'general')
        remediation = rule.get('remediation', '')
        gjb_ref = rule.get('gjb_ref', '')
        
        cmd_result = await self.execute_command(command)
        
        output = cmd_result.get('stdout', '')
        stderr = cmd_result.get('stderr', '')
        
        if stderr and not output:
            output = f'[ERROR] {stderr}'
        
        passed, analysis = self.analyze_result(output, expected, check_type)
        
        return {
            'rule_id': rule_id,
            'rule_name': rule_name,
            'description': description,
            'status': 'pass' if passed else 'fail',
            'command': command,
            'output': output[:1000],
            'expected': expected,
            'actual': output[:200],
            'analysis': analysis,
            'severity': severity,
            'category': category,
            'remediation': remediation,
            'gjb_ref': gjb_ref
        }
