# 매장 상세정보 컬럼 추가 스크립트
# 실행 전: DB 연결 정보가 .env에 맞는지 확인하세요.

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"ssl": {"ssl_ca": ""}})

ALTER_SQL = '''
ALTER TABLE posts
  ADD COLUMN place_name VARCHAR(255),
  ADD COLUMN place_address VARCHAR(255),
  ADD COLUMN place_phone VARCHAR(50),
  ADD COLUMN place_category VARCHAR(255),
  ADD COLUMN place_url VARCHAR(255);
'''

def main():
    with engine.connect() as conn:
        try:
            conn.execute(text(ALTER_SQL))
            print("[OK] posts 테이블에 매장 상세정보 컬럼이 추가되었습니다.")
        except Exception as e:
            print("[ERROR] 컬럼 추가 실패:", e)

if __name__ == "__main__":
    main()
