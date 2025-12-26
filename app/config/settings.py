"""应用配置模块

使用 Pydantic Settings 管理应用配置，支持从 .env 文件加载环境变量
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置类"""
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-here"  # 默认值，建议在生产环境中通过环境变量设置
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 应用配置
    APP_TITLE: str = "排程系统"
    APP_DESCRIPTION: str = "订单排程系统API"
    APP_VERSION: str = "1.0.0"
    
    # 管理员配置
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password"
    
    # MySQL 配置 - 从环境变量加载
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "yourrootpw"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: str = "3306"
    MYSQL_DB: str = "plan_db"
    
    # 数据库配置 - 优先使用DATABASE_URL，否则从MySQL配置构建
    DATABASE_URL: str = ""
    ECHO_SQL: bool = False  # 是否打印SQL日志
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果没有显式设置DATABASE_URL，从MySQL配置构建
        if not self.DATABASE_URL:
            if os.path.exists("dev.db"):  # 检查开发数据库文件是否存在
                self.DATABASE_URL = "sqlite:///./dev.db"
            else:
                self.DATABASE_URL = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
    
    class Config:
        env_file = ".env"  # 从.env文件加载配置


# 创建全局配置实例
settings = Settings()