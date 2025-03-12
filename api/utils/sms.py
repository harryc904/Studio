from tencentcloud.sms.v20210111 import sms_client, models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from fastapi import HTTPException
import random
import json
from datetime import datetime, timedelta

from api.config import (
    TENCENT_SECRET_ID,
    TENCENT_SECRET_KEY,
    SMS_SIGN,
    REGISTER_TEMPLATE_ID,
    LOGIN_TEMPLATE_ID,
    SMS_REGION,
    SMS_APPID,
)
from .db import get_db_connection

from api.utils.logger import get_logger

logger = get_logger(__name__)

# 发送验证码
async def send_verification_code(phone_number: str, purpose: int):
    if purpose == 1:  # 登录
        user = get_user_by_phone(phone_number)
        if not user:
            raise HTTPException(
                status_code=400,
                detail="Phone number is not registered. Please register first.",
            )

    # 设置腾讯云 SMS 服务的证书
    cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
    client = sms_client.SmsClient(cred, SMS_REGION)
    # 生成验证码
    verification_code = str(random.randint(100000, 999999))

    # 选择适当的模板 ID 和 Purpose
    if purpose == 0:  # 注册
        TEMPLATE_ID = REGISTER_TEMPLATE_ID
    elif purpose == 1:  # 登录
        TEMPLATE_ID = LOGIN_TEMPLATE_ID
    else:
        raise HTTPException(status_code=400, detail="Invalid purpose value")

    # 构建发送请求的消息
    req = models.SendSmsRequest()
    params = {
        "PhoneNumberSet": [phone_number],
        "SmsSdkAppId": SMS_APPID,
        "TemplateId": TEMPLATE_ID,
        "SignName": SMS_SIGN,
        "TemplateParamSet": [verification_code, "5"],
    }
    req.from_json_string(json.dumps(params))

    try:
        # 发送短信验证码
        response = client.SendSms(req)
        logger.info(f"SMS sent to {phone_number}: {response.to_json_string()}")

        # 储存验证码到数据库，并记录用途
        store_verification_code(phone_number, verification_code, purpose)
        return {"message": "Verification code sent successfully"}

    except TencentCloudSDKException as err:
        logger.error(f"Error sending SMS: {err}")
        raise HTTPException(status_code=500, detail=f"Error sending SMS: {err}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred")

# 存储验证码
def store_verification_code(phone_number: str, verification_code: str, purpose: int):
    # 获取当前时间和过期时间（5分钟后）
    expiration_time = datetime.now() + timedelta(minutes=5)

    conn = None
    try:
        # 连接到数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查是否已存在相同手机号和用途的验证码记录
        cursor.execute(
            """
            SELECT COUNT(*) FROM verification_codes
            WHERE phone_number = %s AND purpose = %s;
        """,
            (phone_number, purpose),
        )

        existing_record = cursor.fetchone()[0]

        if existing_record > 0:
            # 如果记录存在，更新验证码和过期时间
            cursor.execute(
                """
                UPDATE verification_codes
                SET verification_code = %s, expiration_time = %s
                WHERE phone_number = %s AND purpose = %s;
            """,
                (verification_code, expiration_time, phone_number, purpose),
            )
            conn.commit()
            logger.info(f"Updated verification code for {phone_number} with purpose {purpose}")
        else:
            # 如果记录不存在，插入新的验证码记录
            cursor.execute(
                """
                INSERT INTO verification_codes (phone_number, verification_code, expiration_time, purpose)
                VALUES (%s, %s, %s, %s);
            """,
                (phone_number, verification_code, expiration_time, purpose),
            )
            conn.commit()
            logger.info(f"Inserted new verification code for {phone_number} with purpose {purpose}")

    except Exception as e:
        logger.error(f"Error storing verification code: {e}")
        raise HTTPException(status_code=500, detail="Error storing verification code")
    finally:
        if conn:
            conn.close()

# 从数据库中获取有效验证码
def get_verification_code(phone_number: str, purpose: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查询指定手机号和用途的验证码
            cur.execute(
                """
                SELECT verification_code, expiration_time
                FROM verification_codes
                WHERE phone_number = %s AND purpose = %s
                ORDER BY expiration_time DESC
                LIMIT 1
            """,
                (phone_number, purpose),
            )

            result = cur.fetchone()
            if result:
                stored_code, expiration_time = result
                # 如果验证码过期，返回 None
                if expiration_time < datetime.utcnow():
                    return None
                return stored_code
            return None
    except Exception as e:
        logger.error(f"Error fetching verification code: {e}")
        return None
    finally:
        if conn:
            conn.close()

# 根据手机号获取用户
def get_user_by_phone(phone_number: str):
    from ..services.auth_service import get_user_from_db
    return get_user_from_db(phone_number, is_email=False)