
# ====== IMPORTS (최상단에 위치) ======
from fastapi import FastAPI, Request, Depends, Form, HTTPException, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, text, func
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv
import os
from Database import Like, User, Post, Comment, get_db

# --- 7. 서버 실행 ---
app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

templates = Jinja2Templates(directory="templates")

# 정적 파일(이미지) 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 글 수정 API (app 인스턴스 생성 이후, 게시글 관련 라우터 아래에 위치) ---
@app.post("/api/posts/{post_id}/edit")
def edit_post(
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    is_notice: int = Form(0),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return JSONResponse(status_code=404, content={"detail": "게시글이 없습니다."})
    if post.user_id != int(user_id):
        return JSONResponse(status_code=403, content={"detail": "수정 권한이 없습니다."})
    post.title = title
    post.content = content
    post.category = category.upper()
    post.is_notice = is_notice
    db.commit()
    return {"message": "게시글이 성공적으로 수정되었습니다!", "redirect": f"/post/{post_id}"}


@app.post("/api/upload-image")
def upload_image(image: UploadFile = File(...)):
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, image.filename)
    with open(file_location, "wb") as f:
        f.write(image.file.read())
    image_url = f"/static/uploads/{image.filename}"
    return {"image_url": image_url}

# 최신순 게시글 리스트
@app.get("/api/posts/{category}/latest")
def get_posts_latest(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()).order_by(Post.is_notice.desc(), Post.created_at.desc()).all()
    return [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "nickname": post.owner.nickname if post.owner else "",
            "created_at": post.created_at,
            "comment_count": len(post.comments),
            "like_count": len(getattr(post, 'likes', [])) if hasattr(post, 'likes') else 0,
            "is_notice": getattr(post, 'is_notice', 0)
        }
        for post in posts
    ]

# 인기순 게시글 리스트 (댓글 수 기준)
@app.get("/api/posts/{category}/popular")
def get_posts_popular(category: str, db: Session = Depends(get_db)):
    from Database import Like
    posts = db.query(Post).filter(Post.category == category.upper()) \
        .outerjoin(Post.likes) \
        .group_by(Post.id) \
        .order_by(func.count(Like.id).desc(), Post.created_at.desc()).all()
    return [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "nickname": post.owner.nickname if post.owner else "",
            "created_at": post.created_at,
            "comment_count": len(post.comments),
            "like_count": len(getattr(post, 'likes', [])) if hasattr(post, 'likes') else 0
        }
        for post in posts
    ]

@app.get("/test/users")
def test_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "nickname": u.nickname, "hashed_password": u.hashed_password} for u in users]

@app.get("/test/users/columns")
def test_users_columns(db: Session = Depends(get_db)):
    result = db.execute(text("SHOW COLUMNS FROM users"))
    columns = [row[0] for row in result]
    return {"columns": columns}

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("LOGIN.html", {"request": request})

# 회원가입 페이지 라우터
@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("SIGNUP.html", {"request": request})

@app.post("/login")
def login_post(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.hashed_password != password:
        return {"error": "이메일 또는 비밀번호가 올바르지 않습니다."}
    return {"message": "로그인 성공", "redirect": "/main"}

@app.post("/api/login")
def api_login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.hashed_password != password:
        return JSONResponse(status_code=400, content={"detail": "이메일이나 비밀번호가 일치하지 않습니다."})
    return {
        "message": "로그인 성공",
        "redirect": "/main",
        "user_id": user.id,
        "nickname": user.nickname,
        "is_admin": user.is_admin
    }

# 회원가입 API
@app.post("/api/signup")
def api_signup(
    nickname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 이메일 중복 체크
    if db.query(User).filter(User.email == email).first():
        return JSONResponse(status_code=400, content={"detail": "이미 사용 중인 이메일입니다."})
    # 닉네임 중복 체크
    if db.query(User).filter(User.nickname == nickname).first():
        return JSONResponse(status_code=400, content={"detail": "이미 사용 중인 닉네임입니다."})
    # 새 유저 생성
    new_user = User(email=email, nickname=nickname, hashed_password=password, is_admin=0)
    db.add(new_user)
    db.commit()
    return {"message": "회원가입 성공", "redirect": "/login"}

@app.post("/api/posts")
def create_post(
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    user_id: int = Form(...),
    is_notice: int = Form(0),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 사용자입니다."})
    new_post = Post(category=category.upper(), title=title, content=content, owner=user, is_notice=is_notice)
    db.add(new_post)
    db.commit()
    return {"message": "게시글이 성공적으로 등록되었습니다!", "redirect": "/community"}

@app.get("/community", response_class=HTMLResponse)
def community_page(request: Request):
    return templates.TemplateResponse("COMMUNITY.html", {"request": request})

@app.get("/category/solo", response_class=HTMLResponse)
def category_solo_page(request: Request):
    return templates.TemplateResponse("SOLO.html", {"request": request})

@app.get("/category/date", response_class=HTMLResponse)
def category_date_page(request: Request):
    return templates.TemplateResponse("DATE.html", {"request": request})

@app.get("/category/work", response_class=HTMLResponse)
def category_work_page(request: Request):
    return templates.TemplateResponse("WORK.html", {"request": request})

@app.get("/category/etc", response_class=HTMLResponse)
def category_etc_page(request: Request):
    return templates.TemplateResponse("ETC.html", {"request": request})

@app.get("/community/write", response_class=HTMLResponse)
def community_write_page(request: Request):
    return templates.TemplateResponse("WRITE.html", {"request": request})

@app.get("/write", response_class=HTMLResponse)
def write_page(request: Request):
    return templates.TemplateResponse("WRITE.html", {"request": request})

@app.get("/aichat", response_class=HTMLResponse)
def aichat_page(request: Request):
    return templates.TemplateResponse("AICHAT.html", {"request": request})

@app.get("/api/posts/{category}")
def get_posts_by_category(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()).all()
    return [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "nickname": post.owner.nickname if post.owner else "",
            "created_at": post.created_at,
            "comment_count": len(post.comments),
            "like_count": len(getattr(post, 'likes', [])) if hasattr(post, 'likes') else 0
        }
        for post in posts
    ]

@app.get("/main", response_class=HTMLResponse)
def main_page(request: Request):
    return templates.TemplateResponse("테이스트메이트.html", {"request": request})

@app.get("/post_detail/{post_id}", response_class=HTMLResponse)
def post_detail_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return templates.TemplateResponse("post_detail.html", {"request": request, "error": "게시글을 찾을 수 없습니다."}, status_code=404)
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})

@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return templates.TemplateResponse("post_detail.html", {"request": request, "error": "게시글을 찾을 수 없습니다."}, status_code=404)
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})

@app.get("/community/post/{post_id}", response_class=HTMLResponse)
def community_post_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return templates.TemplateResponse("post_detail.html", {"request": request, "error": "게시글을 찾을 수 없습니다."}, status_code=404)
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})

@app.get("/api/posts/detail/{post_id}")
def api_post_detail(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return JSONResponse(status_code=404, content={"detail": "게시글이 없습니다."})
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.owner.nickname if post.owner else "",
        "user_id": post.user_id,
        "category": post.category,
        "is_notice": getattr(post, 'is_notice', 0),
        "date": post.created_at.strftime("%Y-%m-%d %H:%M"),
        "comments": [
            {
                "author": c.owner.nickname if c.owner else "",
                "content": c.content,
                "date": c.created_at.strftime("%Y-%m-%d %H:%M")
            } for c in comments
        ]
    }

@app.post("/api/comments")
def create_comment(content: str = Form(...), post_id: int = Form(...), user_id: int = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not user or not post:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 사용자 또는 게시글입니다."})
    new_comment = Comment(content=content, owner=user, post=post)
    db.add(new_comment)
    db.commit()
    return {"message": "댓글이 등록되었습니다."}

@app.post("/api/posts/{post_id}/like")
def toggle_like(post_id: int, user_id: int = Form(...), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    user = db.query(User).filter(User.id == user_id).first()
    if not post or not user:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 게시글 또는 사용자입니다."})
    # 이미 좋아요를 눌렀는지 확인
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "좋아요 취소", "liked": False, "like_count": db.query(Like).filter(Like.post_id == post_id).count()}
    else:
        new_like = Like(post_id=post_id, user_id=user_id)
        db.add(new_like)
        db.commit()
        return {"message": "좋아요 추가", "liked": True, "like_count": db.query(Like).filter(Like.post_id == post_id).count()}

@app.get("/api/posts/{post_id}/is_liked")
def is_post_liked(post_id: int, user_id: int, db: Session = Depends(get_db)):
    liked = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first() is not None
    return {"liked": liked}

# 댓글순 게시글 리스트 (댓글 많은 순)
@app.get("/api/posts/{category}/comment")
def get_posts_comment(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()) \
        .outerjoin(Post.comments) \
        .group_by(Post.id) \
        .order_by(func.count(Comment.id).desc(), Post.created_at.desc()).all()
    return [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "nickname": post.owner.nickname if post.owner else "",
            "created_at": post.created_at,
            "comment_count": len(post.comments),
            "like_count": len(getattr(post, 'likes', [])) if hasattr(post, 'likes') else 0
        }
        for post in posts
    ]

@app.post("/fix-etc-category")
def fix_etc_category(db: Session = Depends(get_db)):
    # 'etc', 'Etc', 'eTc' 등 소문자/대소문자 혼용된 ETC 게시글을 모두 'ETC'로 일괄 변경
    updated = db.query(Post).filter(func.lower(Post.category) == 'etc').update({Post.category: 'ETC'}, synchronize_session=False)
    db.commit()
    return {"updated": updated, "message": "ETC 카테고리 일괄 수정 완료"}


from fastapi import Body
from typing import Optional

@app.post("/api/posts/{post_id}/delete")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return JSONResponse(status_code=404, content={"detail": "게시글이 없습니다."})
    try:
        data = await request.json()
        user_id = data.get("user_id")
    except Exception:
        user_id = None
    if not user_id:
        return JSONResponse(status_code=400, content={"detail": "로그인 정보가 필요합니다."})
    if post.user_id != int(user_id):
        return JSONResponse(status_code=403, content={"detail": "삭제 권한이 없습니다."})
    db.delete(post)
    db.commit()
    return {"message": "삭제 완료"}
