# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 파일의 변수명과 동일하게 작성
    KAKAO_REST_API_KEY: str
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    GEMINI_API_KEY: str

    # extra="ignore" 를 추가하면 .env에 선언되지 않은 잉여 변수가 있어도 에러가 나지 않습니다.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# 전역에서 사용할 설정 객체 생성
settings = Settings()