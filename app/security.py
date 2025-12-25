"""安全模块：密码哈希与校验（中文说明）

- 使用 Passlib 管理密码哈希，优先采用 pbkdf2_sha256，兼容 bcrypt。
- 对于 bcrypt 的 72 字节限制，哈希前会做截断保护，避免运行时错误。
"""

from passlib.context import CryptContext

# 优先使用 pbkdf2_sha256，若环境可用则仍可兼容 bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """对明文密码进行哈希并返回哈希字符串。

    注意：若密码过长（>72 字节），为兼容 bcrypt 会进行截断处理。
    """
    if isinstance(password, str):
        pw_bytes = password.encode('utf-8')
    else:
        pw_bytes = password
    if len(pw_bytes) > 72:
        password = pw_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配；任意异常视为验证失败。"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False
