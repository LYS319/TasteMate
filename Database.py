# Database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"ssl": {"ssl_ca": ""}})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
    # 추가된 테이블과의 관계
    user_logs = relationship("UserLog", back_populates="user", cascade="all, delete-orphan")
    user_profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    location_logs = relationship("LocationLog", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    payment_logs = relationship("PaymentLog", back_populates="user", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_notice = Column(Integer, default=0)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    place_name = Column(String(255), nullable=True)
    place_address = Column(String(255), nullable=True)
    place_phone = Column(String(50), nullable=True)
    place_category = Column(String(255), nullable=True)
    place_url = Column(String(255), nullable=True)
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


class FriendRequest(Base):
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"))
    to_user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Friend(Base):
    __tablename__ = "friends"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── 사용자 행동 로그 ──────────────────────────────────────────
# 어떤 카테고리를 얼마나 검색/추천받았는지 기록
class UserLog(Base):
    __tablename__ = "user_logs"
    id        = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action    = Column(String(50))    # "search", "recommend", "click"
    category  = Column(String(50))    # "혼밥", "데이트", "회식", "기타"
    keyword   = Column(String(200))   # 검색어 또는 챗봇 입력 내용
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="user_logs")


# ── 사용자 취향 프로필 ────────────────────────────────────────
# AI 챗봇이 추출한 TASTE_DATA 누적 저장 (user당 1행)
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id                = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id           = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_alcohol = Column(String(100))   # "소주", "맥주", "와인" 등
    preferred_snack   = Column(String(100))   # "치킨", "삼겹살", "피자" 등
    situation         = Column(String(50))    # "혼밥", "데이트", "회식"
    region            = Column(String(100))   # "강남구", "마포구" 등
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="user_profile")


# ── 위치 히스토리 ─────────────────────────────────────────────
# 어느 지역에서 주로 검색하는지 기록 (데이터 판매용 집계에 활용)
class LocationLog(Base):
    __tablename__ = "location_logs"
    id        = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lat       = Column(Float)
    lon       = Column(Float)
    region    = Column(String(100))   # 역지오코딩 결과 예: "서울 강남구"
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="location_logs")


# ── 구독 정보 ─────────────────────────────────────────────────
class Subscription(Base):
    __tablename__ = "subscriptions"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan        = Column(String(20))              # "basic"(2900) / "premium"(5900)
    status      = Column(String(20), default="active")  # active / cancelled / expired
    started_at  = Column(DateTime, default=datetime.utcnow)
    expires_at  = Column(DateTime)                # 다음 결제일 (30일 후)
    payment_key = Column(String(255))             # 토스 paymentKey (정기 결제용)
    user = relationship("User", back_populates="subscription")


# ── 결제 로그 ─────────────────────────────────────────────────
class PaymentLog(Base):
    __tablename__ = "payment_logs"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id     = Column(String(100), unique=True)   # 주문 고유 ID (TM-userId-uuid)
    amount       = Column(Integer)                    # 결제 금액 (원)
    payment_type = Column(String(50))                 # "subscription" / "reservation"
    status       = Column(String(20), default="pending")  # pending / success / fail / cancel
    paid_at      = Column(DateTime, default=datetime.utcnow)
    toss_key     = Column(String(255), nullable=True) # 토스 paymentKey (승인 후 저장)
    user = relationship("User", back_populates="payment_logs")


# ← 모든 모델 정의 후에 create_tables 위치
def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()