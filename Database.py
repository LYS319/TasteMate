import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. .env 파일 로드
load_dotenv()

# 2. .env에서 개별 항목 읽기 (변수명이 .env와 정확히 일치해야 함)
DB_USER = os.getenv("TIDB_USER")      # 예: 'root'
DB_PW = os.getenv("TIDB_PASSWORD")    # 예: 'password'
DB_HOST = os.getenv("TIDB_HOST")      # 사용자님이 추가하신 주소
DB_PORT = os.getenv("TIDB_PORT", "4000") # 기본값 4000
DB_NAME = os.getenv("TIDB_NAME", "test") # 기본값 test

# 3. 필수 정보 확인 (에러 방지용)
if not all([DB_USER, DB_PW, DB_HOST]):
    raise ValueError("❌ .env 파일에 TIDB_USER, TIDB_PASSWORD, TIDB_HOST 중 누락된 항목이 있습니다.")

# 4. DATABASE_URL 조립 (TiDB 전용 SSL 설정 포함)
# 
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl_verify_cert=true&ssl_verify_identity=true"

# 5. 엔진 생성 및 세션 설정
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션 의존성 주입 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()