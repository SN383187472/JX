"""
安全基线核查平台 - 配置文件

配置项说明:
    - APP_NAME: 应用名称
    - APP_VERSION: 应用版本
    - SECRET_KEY: JWT签名密钥 (生产环境必须修改)
    - DATABASE_URL: 数据库连接字符串
    - ACCESS_TOKEN_EXPIRE_MINUTES: Token过期时间(分钟)
    - DEFAULT_ADMIN_USER/PASS: 默认管理员账号

注意事项:
    - 生产环境务必修改 SECRET_KEY
    - 首次登录后修改默认密码
    - 可通过 .env 文件覆盖配置

版本: v2.3.0
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    """
    应用配置类
    
    可通过环境变量或.env文件覆盖默认配置
    """
    
    # ============ 应用信息 ============
    APP_NAME: str = "基线核查平台"
    APP_VERSION: str = "2.3.0"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # ============ 数据库配置 ============
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/database/baseline.db"
    
    # ============ 认证配置 ============
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # Token有效期: 24小时
    
    # ============ 默认账号 ============
    # 首次启动自动创建，登录后请立即修改密码
    DEFAULT_ADMIN_USER: str = "admin"
    DEFAULT_ADMIN_PASS: str = "admin123"
    
    # ============ 路径配置 ============
    RULES_DIR: str = os.path.join(BASE_DIR, "rules")      # 规则库目录
    REPORTS_DIR: str = os.path.join(BASE_DIR, "reports")  # 报告存储目录
    LOGS_DIR: str = os.path.join(BASE_DIR, "logs")        # 日志存储目录
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
