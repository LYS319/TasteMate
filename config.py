# 병합본 config.py (TasteMate-Community-junyoung 기준)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    KAKAO_REST_API_KEY: str
    SECRET_KEY: str = "임시_시크릿_키"
    ALGORITHM: str = "HS256"
    TIDB_USER: str
    TIDB_PASSWORD: str
    TIDB_HOST: str
    TIDB_PORT: str = "4000"
    TIDB_DB_NAME: str = "test"
    GEMINI_API_KEY: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.TIDB_USER}:{self.TIDB_PASSWORD}@"
            f"{self.TIDB_HOST}:{self.TIDB_PORT}/{self.TIDB_DB_NAME}"
            "?ssl_verify_cert=true&ssl_verify_identity=true"
        )
settings = Settings()
