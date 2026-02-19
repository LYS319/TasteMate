# 병합본 Database.py (TasteMate-Community-junyoung 기준)
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv

load_dotenv()
user = os.getenv("TIDB_USER")
password = os.getenv("TIDB_PASSWORD")
host = os.getenv("TIDB_HOST")
port = os.getenv("TIDB_PORT")
db = os.getenv("TIDB_DB_NAME")
# 3. TiDB Cloud용 SSL 옵션이 포함된 URL 생성
# TiDB Cloud Serverless는 보안을 위해 암호화된 연결(SSL/TLS)이 필수입니다.
DATABASE_URL = (
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    "?ssl_verify_cert=true&ssl_verify_identity=true"
)

# 4. 엔진 생성 및 PyMySQL TLS 강제 설정
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    connect_args={
        "ssl": {
            "fake_flag_to_enable_tls": True  # PyMySQL에서 보안 연결을 활성화하는 핵심 설정
        }
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 데이터 모델 (기존 코드 유지) ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(100))
    is_admin = Column(Integer, default=0)
    status = Column(String(50), default="정상")
    created_at = Column(DateTime, default=datetime.utcnow)
    posts = relationship("Post", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_notice = Column(Integer, default=0)
    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    post = relationship("Post", back_populates="likes")
    user = relationship("User")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    owner = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chat_history")

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String(255), unique=True)
    name = Column(String(255))
    category = Column(String(255))
    lat = Column(Float)
    lon = Column(Float)
    rating = Column(Float)

# 테이블 생성 함수
def create_tables():
    Base.metadata.create_all(bind=engine)

# DB 세션 종속성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()