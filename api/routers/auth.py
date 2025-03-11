from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional, Union
from pydantic import EmailStr

from ..schemas.auth import Token, TokenData, UserRegisterRequest, UserRegisterResponse, LoginRequestForm
from ..schemas.user import User, UserInDB
from ..services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_user_by_phone,
    get_user_from_db,
    get_verification_code,
    send_verification_code,
    store_verification_code
)
from ..config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, logger

router = APIRouter(prefix="", tags=["认证"])

# 请求验证码接口
@router.post("/request_verification_code")
async def request_verification_code(phone_number: str, purpose: int):
    # 通过腾讯云接口发送验证码
    return await send_verification_code(phone_number, purpose)


@router.post("/register", response_model=UserRegisterResponse)
async def register_user(user: UserRegisterRequest):
    # 验证手机号验证码
    stored_code = get_verification_code(user.phone_number, purpose=0)  # 0: 注册用途
    if not stored_code:
        raise HTTPException(
            status_code=400, detail="Verification code expired or not sent"
        )

    if stored_code != user.verification_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    # 调用服务层处理注册逻辑
    try:
        new_user = await register_user_service(user)
        
        # 生成 JWT 访问令牌
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user["email"]}, expires_delta=access_token_expires
        )

        return UserRegisterResponse(
            user_id=new_user["user_id"],
            username=new_user["username"],
            email=new_user["email"],
            phone_number=new_user["phone_number"],
            access_token=access_token,
        )
    except HTTPException as e:
        # 捕获已定义的 HTTPException 并返回具体错误
        raise e
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 登录接口
@router.post("/login", response_model=Token)
async def login(form_data: LoginRequestForm):
    # 情况 1：手机号或邮箱加密码登录
    if form_data.username and form_data.password:
        user = authenticate_user(form_data.username, form_data.password)

        if not user:
            logger.warning("Login failed for user: %s", form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        logger.info("User %s logged in successfully", user.email)
        return {"access_token": access_token, "token_type": "bearer"}

    # 情况 2：手机号加验证码登录
    elif form_data.phone_number and form_data.verification_code:
        # 从数据库获取用户信息，检查手机号是否存在
        user = get_user_by_phone(form_data.phone_number)
        if not user:
            logger.warning("Login failed for phone: %s", form_data.phone_number)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Phone number not registered",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 获取数据库中存储的验证码
        stored_code = get_verification_code(
            form_data.phone_number, purpose=1
        )  # 1: 登录用途
        if not stored_code:
            raise HTTPException(
                status_code=400, detail="Verification code expired or not sent"
            )

        # 对比验证码
        if stored_code != form_data.verification_code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        logger.info("User %s logged in successfully with phone number", user.email)
        return {"access_token": access_token, "token_type": "bearer"}

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login data provided",
        )


# 获取当前用户信息的接口
@router.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    # 直接返回当前用户信息
    return current_user


# 登出接口（仅用于前端指示，JWT 无状态无法在后端登出）
@router.post("/logout")
async def logout():
    return {"msg": "User logged out successfully"}