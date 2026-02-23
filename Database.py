# Database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"ssl": {"ssl_ca": ""}})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터 모델 (중복 제거, 모든 필드 포함)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(100))
    is_admin = Column(Integer, default=0)
    status = Column(String(50), default="정상")
    created_at = Column(DateTime, default=datetime.utcnow)  # 회원가입 일시
    posts = relationship("Post", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    # image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_notice = Column(Integer, default=0)  # 0: 일반글, 1: 공지글
    lat = Column(Float, nullable=True)  # 위도
    lon = Column(Float, nullable=True)  # 경도
    # 매장 상세정보(선택 시 저장)
    place_name = Column(String(255), nullable=True)
    place_address = Column(String(255), nullable=True)
    place_phone = Column(String(50), nullable=True)
    place_category = Column(String(255), nullable=True)
    place_url = Column(String(255), nullable=True)
    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")

# 좋아요 테이블
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

# 테이블 생성
def create_tables():
    Base.metadata.create_all(bind=engine)

# DB 세션 종속성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text)  # 사용자 질문 [cite: 72]
    response = Column(Text)  # AI 답변
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_history")

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String, unique=True) # 카카오 맵 API 고유 ID
    name = Column(String)
    category = Column(String)
    lat = Column(Float)
    lon = Column(Float)
    rating = Column(Float)
    