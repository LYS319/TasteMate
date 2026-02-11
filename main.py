import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base

# --- 1. 환경 변수 및 MySQL DB 설정 (config.py 연동) ---
# 기존 dotenv 로드 코드를 지우고 config 파일에서 settings 객체를 가져옵니다.
from config import settings 

# MySQL 연결 설정 (pool_pre_ping으로 DB 연결 끊김 방지)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. 데이터베이스 모델 ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(100))
    is_admin = Column(Integer, default=0) 
    status = Column(String(50), default="정상") 
    posts = relationship("Post", back_populates="owner")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True)
    title = Column(String(255))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="posts")

Base.metadata.create_all(bind=engine)

# --- 3. FastAPI 설정 ---
app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- 4. HTML 페이지 연결 라우팅 ---
@app.get("/", response_class=HTMLResponse)
def home(): return FileResponse("login.html")

@app.get("/login", response_class=HTMLResponse)
def login_page(): return FileResponse("login.html")

@app.get("/signup", response_class=HTMLResponse)
def signup_page(): return FileResponse("signup.html")

@app.get("/main", response_class=HTMLResponse)
def main_page(): return FileResponse("main.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page(): return FileResponse("admin.html")

# --- 5. 핵심 인증 API (404 에러 해결 구간) ---
@app.post("/api/signup")
def register(nickname: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # 중복 이메일 체크 (서버 다운 방지)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
    
    new_user = User(email=email, hashed_password=password, nickname=nickname, status="정상")
    db.add(new_user)
    db.commit()
    return {"message": "가입 완료", "redirect": "/login"}

@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.hashed_password == password).first()
    
    if not user: 
        raise HTTPException(status_code=400, detail="이메일이나 비밀번호가 일치하지 않습니다.")
    if user.status == "차단": 
        raise HTTPException(status_code=403, detail="활동이 정지된 계정입니다. 관리자에게 문의하세요.")
    
    redirect_path = "/admin" if user.is_admin == 1 else "/main"
    return {"nickname": user.nickname, "redirect": redirect_path}

# --- 6. 마스터 관리자 전용 제어 API ---
@app.get("/api/admin/users")
def list_users(db: Session = Depends(get_db)): 
    return db.query(User).all()

@app.patch("/api/admin/users/{user_id}/status")
def update_status(user_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: 
        user.status = status
        db.commit()
        return {"message": "Success"}
    raise HTTPException(status_code=404)

@app.patch("/api/admin/users/{user_id}/role")
def update_role(user_id: int, is_admin: int = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: 
        user.is_admin = is_admin
        db.commit()
        return {"message": "Success"}
    raise HTTPException(status_code=404)

@app.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user: 
        db.delete(user)
        db.commit()
        return {"message": "Deleted"}
    raise HTTPException(status_code=404)

@app.get("/api/admin/posts")
def list_posts(db: Session = Depends(get_db)): 
    return db.query(Post).all()

@app.delete("/api/admin/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post: 
        db.delete(post)
        db.commit()
        return {"message": "Deleted"}
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)