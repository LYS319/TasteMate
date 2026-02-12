import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base

from config import settings 

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 데이터 모델 ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(100))
    is_admin = Column(Integer, default=0) 
    status = Column(String(50), default="정상") 
    posts = relationship("Post", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    owner = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- 1. 화면 라우팅 (🚨 모두 templates 폴더 경로로 깔끔하게 수정 완료!) ---
@app.get("/", response_class=HTMLResponse)
def home(): return FileResponse("templates/테이스트메이트.html")
@app.get("/login", response_class=HTMLResponse)
def login_page(): return FileResponse("templates/LOGIN.html")
@app.get("/signup", response_class=HTMLResponse)
def signup_page(): return FileResponse("templates/SIGNUP.html")
@app.get("/main", response_class=HTMLResponse)
def main_page(): return FileResponse("templates/테이스트메이트.html")
@app.get("/admin", response_class=HTMLResponse)
def admin_page(): return FileResponse("templates/admin.html")
@app.get("/community", response_class=HTMLResponse)
def community_page(): return FileResponse("templates/COMMUNITY.html")
@app.get("/category/{cat_name}", response_class=HTMLResponse)
def category_page(cat_name: str): return FileResponse(f"templates/{cat_name.upper()}.html")
@app.get("/write", response_class=HTMLResponse)
def write_page(): return FileResponse("templates/WRITE.html")
@app.get("/aichat", response_class=HTMLResponse)
def aichat_page(): return FileResponse("templates/AICHAT.html")
@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail_page(post_id: int): return FileResponse("templates/post_detail.html")
@app.get("/mypage", response_class=HTMLResponse)
def mypage(): return FileResponse("templates/MYPAGE.html")


# --- 2. 인증 및 마이페이지 API ---
@app.post("/api/signup")
def register(nickname: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first(): raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
    new_user = User(email=email, hashed_password=password, nickname=nickname, status="정상")
    db.add(new_user); db.commit()
    return {"message": "가입 완료", "redirect": "/login"}

@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.hashed_password == password).first()
    if not user: raise HTTPException(status_code=400, detail="이메일이나 비밀번호가 일치하지 않습니다.")
    if user.status == "차단": raise HTTPException(status_code=403, detail="활동 정지 계정입니다.")
    return {"nickname": user.nickname, "user_id": user.id, "is_admin": user.is_admin, "redirect": "/main"}

@app.get("/api/users/{user_id}/me")
def get_my_info(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404)
    return {
        "email": user.email, "nickname": user.nickname, "post_count": len(user.posts), "comment_count": len(user.comments),
        "posts": [{"id": p.id, "category": p.category, "title": p.title, "date": p.created_at.strftime("%Y-%m-%d")} for p in user.posts],
        "comments": [{"id": c.id, "post_id": c.post_id, "content": c.content, "date": c.created_at.strftime("%Y-%m-%d")} for c in user.comments]
    }


# --- 3. 관리자 전용 API ---
@app.get("/api/admin/users")
def list_users(db: Session = Depends(get_db)): return db.query(User).all()

@app.patch("/api/admin/users/{user_id}/status")
def update_status(user_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: user.status = status; db.commit(); return {"message": "Success"}
    raise HTTPException(status_code=404)

@app.patch("/api/admin/users/{user_id}/role")
def update_role(user_id: int, is_admin: int = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: user.is_admin = is_admin; db.commit(); return {"message": "Success"}
    raise HTTPException(status_code=404)

@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: db.delete(user); db.commit(); return {"message": "Deleted"}
    raise HTTPException(status_code=404)

@app.get("/api/admin/users/{user_id}/activity")
def get_user_activity(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404)
    return {
        "nickname": user.nickname, "post_count": len(user.posts), "comment_count": len(user.comments),
        "posts": [{"id": p.id, "category": p.category, "title": p.title, "date": p.created_at.strftime("%Y-%m-%d %H:%M")} for p in user.posts],
        "comments": [{"id": c.id, "post_id": c.post_id, "content": c.content, "date": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in user.comments]
    }

# 🚨 해결 완료: 빠져있던 관리자 게시글 조회 및 삭제 API 🚨
@app.get("/api/admin/posts")
def admin_list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return [{"id": p.id, "category": p.category, "title": p.title, "author": p.owner.nickname if p.owner else "익명", "date": p.created_at.strftime("%Y-%m-%d %H:%M")} for p in posts]

@app.delete("/api/admin/posts/{post_id}")
def admin_delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post: db.delete(post); db.commit(); return {"message": "Deleted"}
    raise HTTPException(status_code=404)


# --- 4. 커뮤니티 데이터 API ---
@app.get("/api/posts/{category}")
def get_posts_by_category(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()).order_by(Post.created_at.desc()).all()
    return [{"id": p.id, "title": p.title, "content": p.content, "date": p.created_at.strftime("%Y-%m-%d"), "author": p.owner.nickname if p.owner else "익명"} for p in posts]

@app.post("/api/posts")
def create_post(user_id: int = Form(...), category: str = Form(...), title: str = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    new_post = Post(user_id=user_id, category=category.upper(), title=title, content=content)
    db.add(new_post); db.commit()
    return {"message": "Success", "redirect": f"/category/{category.lower()}"}

@app.get("/api/posts/detail/{post_id}")
def get_post_detail(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post: raise HTTPException(status_code=404)
    comments = [{"id": c.id, "author": c.owner.nickname if c.owner else "익명", "content": c.content, "date": c.created_at.strftime("%Y-%m-%d %H:%M")} for c in post.comments]
    return {
        "id": post.id, "title": post.title, "content": post.content, 
        "category": post.category, "date": post.created_at.strftime("%Y-%m-%d %H:%M"),
        "author": post.owner.nickname if post.owner else "익명", "comments": comments
    }

@app.post("/api/comments")
def create_comment(post_id: int = Form(...), user_id: int = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    new_comment = Comment(post_id=post_id, user_id=user_id, content=content)
    db.add(new_comment); db.commit()
    return {"message": "Success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)