from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- 1. 기존 보안 및 API 설정 (이것들도 꼭 있어야 합니다!) ---
        KAKAO_REST_API_KEY: str
    SECRET_KEY: str = "임시_시크릿_키"       # JWT 암호화용 (필수)
    ALGORITHM: str = "HS256"                # 암호화 알고리즘

    # --- 2. TiDB (데이터베이스) 연결 정보 ---
    TIDB_USER: str
    TIDB_PASSWORD: str
    TIDB_HOST: str
    TIDB_PORT: str = "4000"
    TIDB_DB_NAME: str = "test"

    # .env 파일을 읽어오도록 설정 (.env 파일이 없으면 시스템 환경변수에서 찾음)
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- 3. 정보를 조합해 DB 접속 URL 자동 생성 (Property) ---
    @property
    def DATABASE_URL(self) -> str:
        # TiDB Cloud는 보안 접속(SSL)이 필수이므로 옵션을 뒤에 붙여줍니다.
        return (
            f"mysql+pymysql://{self.TIDB_USER}:{self.TIDB_PASSWORD}@"
            f"{self.TIDB_HOST}:{self.TIDB_PORT}/{self.TIDB_DB_NAME}"
            "?ssl_verify_cert=true&ssl_verify_identity=true"
        )

        # .env 파일의 변수명과 동일하게 작성
        DATABASE_URL: str

        # extra="ignore" 를 추가하면 .env에 선언되지 않은 잉여 변수가 있어도 에러가 나지 않습니다.
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        # 전역에서 사용할 설정 객체 생성
    settings = Settings()
# 설정 객체 생성 (main.py에서 이걸 가져다 씁니다)
settings = Settings()