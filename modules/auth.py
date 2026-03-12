"""
认证处理器 - JWT Token 认证
兼容 Python 3.9 - 3.12
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import hashlib
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User


class AuthHandler:
    """认证处理器"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def hash_password(self, password: str) -> str:
        """密码哈希 - 使用SHA256"""
        salted = f"{self.secret_key}:{password}"
        return hashlib.sha256(salted.encode()).hexdigest()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.hash_password(plain_password) == hashed_password
    
    def create_token(self, username: str, expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT Token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode = {
            "sub": username,
            "exp": expire
        }
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[dict]:
        """解码JWT Token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None


async def get_current_user(
    request: Request,
    session: AsyncSession,
    auth_handler: AuthHandler
):
    """获取当前登录用户"""
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    payload = auth_handler.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token无效")
    
    # 从数据库获取用户
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user
