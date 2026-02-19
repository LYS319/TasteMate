# 병합본 main.py (TasteMate-Community-junyoung 기준)
# 실제 서비스용으로 최신 기능/라우터/템플릿 반영
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base


from config import settings

# FastAPI 인스턴스 선언 (모든 import 바로 아래, 단 한 번만)
app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- Gemini 챗봇용 ---
from pydantic import BaseModel
from google import genai

class ChatRequest(BaseModel):
    message: str

# --- Top Places API용 모델 ---
class TopPlacesRequest(BaseModel):
    category: str
    lat: float
    lon: float

client = genai.Client(api_key=settings.GEMINI_API_KEY)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
                당신은 모바일 서비스 '테이스트메이트 AI'입니다.

                ⚠️ 반드시 아래 형식으로만 답변하세요.
                - 블로그 스타일 금지
                - 길게 설명 금지
                - 한눈에 보이도록 간결하게 작성
                - 모바일 화면에 맞게 줄 간격 유지

                형식:

                🍺 추천 주류:
                - 한 줄 설명

                🌶 추천 안주 TOP3:
                1. 안주명 – 한 줄 이유
                2. 안주명 – 한 줄 이유
                3. 안주명 – 한 줄 이유

                💡 페어링 포인트:
                - 두 줄 이내 요약

                사용자 질문:
                {request.message}
            """
        )
        return {"reply": response.text}
    except Exception as e:
        print("🔥 Gemini 에러:", e)
        return {"reply": "AI 연결에 문제가 발생했습니다."}


# --- 위치 기반 인기 장소 추천 API ---
@app.post("/api/top-places")
async def top_places(request: TopPlacesRequest):
    # 실제 구현에서는 외부 API 또는 DB에서 장소를 조회해야 함
    # 여기서는 예시로 mock 데이터 반환
    mock_places = [
        {"name": f"{request.category} 맛집{i+1}", "address": f"서울시 어딘가 {i+1}", "map_url": f"https://map.example.com/{i+1}"}
        for i in range(5)
    ]
    return {"places": mock_places}

load_dotenv()

# DB 설정
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- [데이터 모델 정의] ---
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
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_notice = Column(Integer, default=0) 

    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    
    owner = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chat_history")

Base.metadata.create_all(bind=engine)

script_dir = os.path.dirname(__file__)
static_path = os.path.join(script_dir, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

food_path = os.path.join(script_dir, "food")
app.mount("/food", StaticFiles(directory=food_path), name="food")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- [1. 화면 라우팅] ---
@app.get("/")
@app.get("/main", response_class=HTMLResponse)
def home(): return FileResponse("templates/테이스트메이트.html")
@app.get("/login", response_class=HTMLResponse)
def login_page(): return FileResponse("templates/LOGIN.html")
@app.get("/signup", response_class=HTMLResponse)
def signup_page(): return FileResponse("templates/SIGNUP.html")
@app.get("/admin", response_class=HTMLResponse)
def admin_page(): return FileResponse("templates/admin.html")
@app.get("/community", response_class=HTMLResponse)
def community_page(): return FileResponse("templates/COMMUNITY.html")
@app.get("/category/{cat_name}", response_class=HTMLResponse)
def category_page(cat_name: str): return FileResponse(f"templates/{cat_name.upper()}.html")

# --- AI 챗봇 화면 라우터 추가 ---
@app.get("/aichat", response_class=HTMLResponse)
def aichat_page():
    return FileResponse("templates/AICHAT.html")
@app.get("/write", response_class=HTMLResponse)
def write_page(): return FileResponse("templates/WRITE.html")
@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail_page(post_id: int): return FileResponse("templates/post_detail.html")
@app.get("/post_detail/{post_id}", response_class=HTMLResponse)
def post_detail_page2(post_id: int):
    return FileResponse("templates/post_detail.html")
@app.get("/mypage", response_class=HTMLResponse)
def mypage(): return FileResponse("templates/MYPAGE.html")
@app.get("/api/config/kakao")
def get_kakao_key(): return {"key": os.getenv("KAKAO_REST_API_KEY")}

@app.get("/about", response_class=HTMLResponse)
def about_page():
    return FileResponse("templates/about.html")

@app.get("/search", response_class=HTMLResponse)
def search_page():
    return FileResponse("templates/search.html")

# --- [2. 계정 API] ---
@app.post("/api/signup")
def register(nickname: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first(): raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
    new_user = User(email=email, hashed_password=password, nickname=nickname, status="정상")
    db.add(new_user); db.commit()
    return {"message": "가입 완료", "redirect": "/login"}

@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.hashed_password == password).first()
    if not user: raise HTTPException(status_code=400, detail="정보 불일치")
    if user.status == "차단": raise HTTPException(status_code=403, detail="차단된 계정")
    return {"nickname": user.nickname, "user_id": user.id, "is_admin": user.is_admin, "redirect": "/main"}

# --- [3. 게시글 API] ---
@app.post("/api/posts")
def create_post(user_id: int = Form(...), category: str = Form(...), title: str = Form(...), content: str = Form(...), is_notice: int = Form(0), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    actual_notice = is_notice if user and user.is_admin == 1 else 0
    new_post = Post(user_id=user_id, category=category.upper(), title=title, content=content, is_notice=actual_notice)
    db.add(new_post); db.commit()
    return {"message": "Success", "redirect": f"/category/{category.lower()}"}

# 🌟 수정 (PATCH)
@app.patch("/api/posts/{post_id}")
def update_post(post_id: int, title: str = Form(...), content: str = Form(...), user_id: int = Form(...), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or str(post.user_id) != str(user_id): raise HTTPException(status_code=403)
    post.title, post.content = title, content
    db.commit(); return {"message": "Updated"}

# 🌟 삭제 (POST 방식 경로 맞춤)
@app.post("/api/posts/{post_id}/delete")
def delete_post(post_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or str(post.user_id) != str(user_id): raise HTTPException(status_code=403)
    db.delete(post); db.commit(); return {"message": "Deleted"}

@app.get("/api/posts/detail/{post_id}")
def get_post_detail(post_id: int, user_id: int = None, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404)
    is_liked = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first() is not None if user_id else False
    return {
        "id": post.id, "title": post.title, "content": post.content, "category": post.category, "user_id": post.user_id,
        "author": post.owner.nickname if post.owner else "익명", "date": post.created_at.strftime("%Y-%m-%d %H:%M"),
        "like_count": len(post.likes), "is_liked": is_liked, "is_notice": post.is_notice,
        "comments": [{"id": c.id, "user_id": c.user_id, "author": c.owner.nickname, "content": c.content, "date": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in post.comments]
    }

@app.get("/api/posts/{category}")
def get_posts_by_category(category: str, sort: str = "latest", db: Session = Depends(get_db)):
    query = db.query(Post).filter(Post.category == category.upper())
    if sort == "popular": query = query.outerjoin(Post.likes).group_by(Post.id).order_by(Post.is_notice.desc(), func.count(Like.id).desc())
    elif sort == "comment": query = query.outerjoin(Post.comments).group_by(Post.id).order_by(Post.is_notice.desc(), func.count(Comment.id).desc())
    else: query = query.order_by(Post.is_notice.desc(), Post.created_at.desc())
    posts = query.all()
    return [{"id": p.id, "title": p.title, "content": p.content, "date": p.created_at.strftime("%Y-%m-%d"), "author": p.owner.nickname if p.owner else "익명", "like_count": len(p.likes), "comment_count": len(p.comments), "is_notice": p.is_notice} for p in posts]

@app.get("/api/posts/{category}/popular")
def get_posts_popular(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()) \
        .outerjoin(Post.likes) \
        .group_by(Post.id) \
        .order_by(Post.is_notice.desc(), func.count(Like.id).desc(), Post.created_at.desc()).all()
    return [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "nickname": post.owner.nickname if post.owner else "",
            "created_at": post.created_at.strftime("%Y-%m-%d %H:%M"),
            "comment_count": len(post.comments),
            "like_count": len(post.likes),
            "is_notice": post.is_notice
        }
        for post in posts
    ]

# --- [4. 좋아요 및 댓글 API] ---
@app.post("/api/posts/{post_id}/like")
def toggle_like(post_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first()
    if existing: db.delete(existing)
    else: db.add(Like(post_id=post_id, user_id=user_id))
    db.commit()
    return {"liked": not existing, "like_count": db.query(Like).filter(Like.post_id == post_id).count()}

@app.post("/api/comments")
def create_comment(post_id: int = Form(...), user_id: int = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    db.add(Comment(post_id=post_id, user_id=user_id, content=content)); db.commit()
    return {"message": "Success"}

# 🌟 댓글 삭제 (POST 방식 경로 맞춤)
@app.post("/api/comments/{comment_id}/delete")
def delete_comment(comment_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or str(comment.user_id) != str(user_id): raise HTTPException(status_code=403)
    db.delete(comment); db.commit(); return {"message": "Deleted"}

# --- [5. 관리자 전용 API] ---
@app.get("/api/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    today = datetime.now().date()
    return {
        "today_signup": db.query(User).filter(func.date(User.created_at) == today).count(),
        "today_post": db.query(Post).filter(func.date(Post.created_at) == today).count(),
        "today_comment": db.query(Comment).filter(func.date(Comment.created_at) == today).count(),
        "total_user": db.query(User).count()
    }

@app.get("/api/admin/posts")
def admin_list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return [{"id": p.id, "category": p.category, "title": p.title, "author": p.owner.nickname if p.owner else "익명", "date": p.created_at.strftime("%Y-%m-%d %H:%M")} for p in posts]

@app.get("/api/admin/users")
def list_users(db: Session = Depends(get_db)): 
    return [{"id": u.id, "email": u.email, "nickname": u.nickname, "is_admin": u.is_admin, "status": u.status} for u in db.query(User).all()]

@app.get("/game/pinball", response_class=HTMLResponse)
def game_pinball():
    return FileResponse("templates/game_pinball.html")

@app.get("/game/ladder", response_class=HTMLResponse)
def game_ladder():
    return FileResponse("templates/game_ladder.html")

@app.get("/game/calculator", response_class=HTMLResponse)
def game_calculator():
    return FileResponse("templates/game_calculator.html")

@app.get("/game/random_amount", response_class=HTMLResponse)
def game_random_amount():
    return FileResponse("templates/game_random_amount.html")

@app.get("/game/worldcup", response_class=HTMLResponse)
def game_worldcup():
    return FileResponse("templates/game_worldcup.html")



