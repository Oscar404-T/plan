from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    mysql_user: str = Field(..., env="MYSQL_USER")
    mysql_password: str = Field(..., env="MYSQL_PASSWORD")
    mysql_host: str = Field("127.0.0.1", env="MYSQL_HOST")
    mysql_port: int = Field(3306, env="MYSQL_PORT")
    mysql_db: str = Field("plan_db", env="MYSQL_DB")

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"


settings = Settings()
