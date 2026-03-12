"""
安全基线核查平台 - 数据库模型定义

数据表:
    - User: 用户表，存储用户账号信息
    - Target: 目标表，存储待扫描目标信息
    - ScanResult: 结果表，存储扫描结果

支持的数据库: SQLite (默认)

版本: v2.3.0
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """
    用户表
    
    存储系统用户账号信息
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, comment="用户名")
    password_hash = Column(String(128), comment="密码哈希")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class Target(Base):
    """
    检测目标表
    
    存储待扫描的目标信息，支持操作系统和数据库类型
    
    目标类型:
        - 操作系统: kylin, centos, ubuntu, windows7, windows10, windows2012
        - 数据库: dameng, mysql, oracle
    """
    __tablename__ = "targets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), comment="目标名称")
    host = Column(String(100), comment="主机地址")
    port = Column(Integer, comment="SSH/WinRM端口")
    target_type = Column(String(20), comment="目标类型")
    
    # 系统连接参数
    username = Column(String(50), comment="SSH/WinRM用户名")
    password = Column(String(100), comment="SSH/WinRM密码")
    
    # 数据库连接参数 (仅数据库类型需要)
    db_port = Column(Integer, nullable=True, comment="数据库端口")
    db_username = Column(String(50), nullable=True, comment="数据库用户名")
    db_password = Column(String(100), nullable=True, comment="数据库密码")
    db_name = Column(String(100), nullable=True, comment="数据库名/SID")
    
    # Windows连接参数
    scheme = Column(String(10), nullable=True, comment="WinRM协议(http/https)")
    
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class ScanResult(Base):
    """
    扫描结果表
    
    存储每次扫描的结果统计和详细数据
    """
    __tablename__ = "scan_results"
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, comment="目标ID")
    target_name = Column(String(100), comment="目标名称")
    target_type = Column(String(20), comment="目标类型")
    scan_time = Column(DateTime, default=datetime.utcnow, comment="扫描时间")
    total_rules = Column(Integer, comment="总规则数")
    passed_rules = Column(Integer, comment="通过规则数")
    failed_rules = Column(Integer, comment="失败规则数")
    result_data = Column(Text, comment="详细结果(JSON格式)")
