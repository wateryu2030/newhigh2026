"""
用户 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.db import get_db
from sqlalchemy.orm import Session
from app.models.database import User, Account, RiskConfig
from pydantic import BaseModel, EmailStr

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    phone: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=pwd_context.hash(user_data.password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # 创建默认账户
    account = Account(user_id=user.id, available_cash=500000, total_assets=500000)
    db.add(account)
    
    # 创建默认风控配置
    risk_config = RiskConfig(user_id=user.id)
    db.add(risk_config)
    
    db.commit()
    
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
