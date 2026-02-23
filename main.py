

import requests
import logging
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI, Request, Depends, Form, HTTPException, File, UploadFile, Body, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.responses import JSONResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, text, func
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv
import os
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

from Database import Like, User, Post, Comment, get_db
from config import settings
from game_ideal_router import router as ideal_router

app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

# --- Gemini AI 챗봇 엔드포인트 ---
class ChatRequest(BaseModel):
    message: str

# --- 카테고리별 인기 장소 API ---
from sqlalchemy import desc

@app.post("/api/top-places")
def top_places_by_category(db: Session = Depends(get_db)):
    # 카테고리별 place_name, place_address, post count 집계
    categories = db.query(Post.category).distinct().all()
    result = {}
    for (category,) in categories:
        # place_name이 null이 아닌 것만 집계
        rows = (
            db.query(
                Post.place_name,
                Post.place_address,
                func.count(Post.id).label("post_count")
            )
            .filter(Post.category == category, Post.place_name != None)
            .group_by(Post.place_name, Post.place_address)
            .order_by(desc("post_count"))
            .limit(5)
            .all()
        )
        result[category] = [
            {
                "place_name": r.place_name,
                "place_address": r.place_address,
                "post_count": r.post_count
            } for r in rows
        ]
    return result

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""
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
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print("🔥 Gemini 에러:", e)
        return {"reply": "AI 연결에 문제가 발생했습니다."}

## 중복 선언 제거 (위에서 이미 선언됨)

# 회사소개 페이지 라우터
@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# 정적 파일(이미지) 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/food", StaticFiles(directory="food"), name="food")

# 계산기 페이지 라우터 추가
@app.get("/game/calculator", response_class=HTMLResponse)
def game_calculator(request: Request):
    return templates.TemplateResponse("game_calculator.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("테이스트메이트.html", {"request": request})
# 회원정보 페이지 라우터
@app.get("/mypage", response_class=HTMLResponse)
def mypage(request: Request):
    return templates.TemplateResponse("MYPAGE.html", {"request": request})

# 내 회원정보 조회 API
@app.get("/api/users/{user_id}/me")
def get_my_info(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    post_count = db.query(Post).filter(Post.user_id == user_id).count()
    comment_count = db.query(Comment).filter(Comment.user_id == user_id).count()
    return {
        "nickname": user.nickname,
        "email": user.email,
        "post_count": post_count,
        "comment_count": comment_count
    }

# 관리자 회원 추방 API
@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    # 관련 게시글/댓글 삭제
    db.query(Post).filter(Post.user_id == user_id).delete()
    db.query(Comment).filter(Comment.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": "회원이 추방되었습니다."}

# 관리자 권한 변경 API
@app.patch("/api/admin/users/{user_id}/role")
def update_user_role(user_id: int, is_admin: int = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    user.is_admin = is_admin
    db.commit()
    return {"message": "권한이 변경되었습니다."}

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
    return {"message": "게시글이 성공적으로 수정되었습니다!", "redirect": f"/post_detail/{post_id}"}


# 닉네임 변경 API
@app.patch("/api/users/{user_id}/nickname")
def update_nickname(user_id: int, nickname: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    user.nickname = nickname
    db.commit()
    return {"message": "닉네임이 변경되었습니다.", "nickname": user.nickname}


# 비밀번호 변경 API
@app.patch("/api/users/{user_id}/password")
def update_password(user_id: int, old_password: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    if user.hashed_password != old_password:
        return JSONResponse(status_code=400, content={"detail": "기존 비밀번호가 일치하지 않습니다."})
    user.hashed_password = password  # 실제 서비스라면 반드시 해싱 필요
    db.commit()
    return {"message": "비밀번호가 변경되었습니다."}


# 이메일 변경 API
@app.patch("/api/users/{user_id}/email")
def update_email(user_id: int, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    user.email = email
    db.commit()
    return {"message": "이메일이 변경되었습니다.", "email": user.email}


@app.post("/api/upload-image")
def upload_image(image: UploadFile = File(...)):
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, image.filename)
    with open(file_location, "wb") as f:
        f.write(image.file.read())
    # image_url = f"/static/uploads/{image.filename}"
    return {"image_url": None}


# 회원 탈퇴(자기 계정 삭제) API
@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    # 관련 게시글/댓글 삭제
    db.query(Post).filter(Post.user_id == user_id).delete()
    db.query(Comment).filter(Comment.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": "회원 탈퇴가 완료되었습니다."}

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
    # 1. 공지글 먼저
    notice_posts = db.query(Post).filter(Post.category == category.upper(), Post.is_notice == 1) \
        .outerjoin(Post.likes) \
        .group_by(Post.id) \
        .order_by(func.count(Like.id).desc(), Post.created_at.desc()).all()
    # 2. 일반글
    normal_posts = db.query(Post).filter(Post.category == category.upper(), Post.is_notice == 0) \
        .outerjoin(Post.likes) \
        .group_by(Post.id) \
        .order_by(func.count(Like.id).desc(), Post.created_at.desc()).all()
    posts = notice_posts + normal_posts
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
    lat: float = Form(None),
    lon: float = Form(None),
    place_name: str = Form(None),
    place_address: str = Form(None),
    place_phone: str = Form(None),
    place_category: str = Form(None),
    place_url: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 사용자입니다."})
    if getattr(user, 'status', None) == '차단':
        return JSONResponse(status_code=403, content={"detail": "차단되어 게시글을 쓸 수 없습니다."})
    # image_url = None
    if image and image.filename:
        upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_location = os.path.join(upload_dir, image.filename)
        with open(file_location, "wb") as f:
            f.write(image.file.read())
        # image_url = f"/static/uploads/{image.filename}"
    new_post = Post(
        category=category.upper(),
        title=title,
        content=content,
        owner=user,
        is_notice=is_notice,
        lat=lat,
        lon=lon,
        place_name=place_name,
        place_address=place_address,
        place_phone=place_phone,
        place_category=place_category,
        place_url=place_url
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {"message": "게시글이 성공적으로 등록되었습니다!", "redirect": f"/post_detail/{new_post.id}", "post_id": new_post.id}

@app.get("/community", response_class=HTMLResponse)
def community_page(request: Request):
    db = next(get_db())
    valid_categories = ["혼밥", "커플", "회식", "기타"]
    posts = db.query(Post).filter(Post.category.in_(valid_categories)).order_by(Post.created_at.desc()).all()
    return templates.TemplateResponse("COMMUNITY.html", {"request": request, "posts": posts})

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
    return templates.TemplateResponse("WRITE.html", {"request": request, "settings": settings})


@app.get("/write", response_class=HTMLResponse)
def write_page(request: Request):
    return templates.TemplateResponse("WRITE.html", {"request": request, "settings": settings})

@app.get("/aichat", response_class=HTMLResponse)
def aichat_page(request: Request):
    return templates.TemplateResponse("AICHAT.html", {"request": request})

@app.get("/api/posts/{category}")
def get_posts_by_category(category: str, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.category == category.upper()).order_by(Post.is_notice.desc(), Post.created_at.desc()).all()
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
    return templates.TemplateResponse("post_detail.html", {"request": request, "settings": settings})

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
        "lat": getattr(post, 'lat', None),
        "lon": getattr(post, 'lon', None),
        "place_name": getattr(post, 'place_name', None),
        "date": post.created_at.strftime("%Y-%m-%d %H:%M"),
        # "image_url": getattr(post, 'image_url', None),
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
    # 댓글 생성 로직 (예시)
    user = db.query(User).filter(User.id == user_id).first()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not user or not post:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 사용자 또는 게시글입니다."})
    new_comment = Comment(content=content, owner=user, post=post)
    db.add(new_comment)
    db.commit()
    return {"message": "댓글이 등록되었습니다."}

@app.get("/game/pinball", response_class=HTMLResponse)
def game_pinball(request: Request):
    return templates.TemplateResponse("game_pinball.html", {"request": request})

@app.get("/game/ladder", response_class=HTMLResponse)
def game_ladder(request: Request):
    return templates.TemplateResponse("game_ladder.html", {"request": request})
    user = db.query(User).filter(User.id == user_id).first()
    post = db.query(Post).filter(Post.id == post_id).first()
    if not user or not post:
        return JSONResponse(status_code=400, content={"detail": "유효하지 않은 사용자 또는 게시글입니다."})
    new_comment = Comment(content=content, owner=user, post=post)
    db.add(new_comment)
    db.commit()
    return {"message": "댓글이 등록되었습니다."}

@app.get("/game/random_amount", response_class=HTMLResponse)
def game_random_amount(request: Request):
    return templates.TemplateResponse("game_random_amount.html", {"request": request})

# 점심 메뉴 월드컵 게임 라우트
@app.get("/game/worldcup", response_class=HTMLResponse)
def game_worldcup(request: Request):
    return templates.TemplateResponse("game_worldcup.html", {"request": request})
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
    # 1. 공지글 먼저
    notice_posts = db.query(Post).filter(Post.category == category.upper(), Post.is_notice == 1) \
        .outerjoin(Post.comments) \
        .group_by(Post.id) \
        .order_by(func.count(Comment.id).desc(), Post.created_at.desc()).all()
    # 2. 일반글
    normal_posts = db.query(Post).filter(Post.category == category.upper(), Post.is_notice == 0) \
        .outerjoin(Post.comments) \
        .group_by(Post.id) \
        .order_by(func.count(Comment.id).desc(), Post.created_at.desc()).all()
    posts = notice_posts + normal_posts
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

# 관리자 페이지 라우터 (app 인스턴스 이후)
@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# 관리자 통계 API
@app.get("/api/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    user_count = db.query(User).count()
    post_count = db.query(Post).count()
    comment_count = db.query(Comment).count()


    from datetime import datetime, timedelta
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    today_signup = db.query(User).filter(User.created_at >= today, User.created_at < tomorrow).count() if hasattr(User, 'created_at') else 0
    today_post = db.query(Post).filter(Post.created_at >= today, Post.created_at < tomorrow).count() if hasattr(Post, 'created_at') else 0
    today_comment = db.query(Comment).filter(Comment.created_at >= today, Comment.created_at < tomorrow).count() if hasattr(Comment, 'created_at') else 0

    return {
        "user_count": user_count,
        "post_count": post_count,
        "comment_count": comment_count,
        "today_signup": today_signup,
        "today_post": today_post,
        "today_comment": today_comment
    }

# 관리자 회원 목록 API (검색/필터 지원)
@app.get("/api/admin/users")
def admin_users(db: Session = Depends(get_db), status: Optional[str] = None, q: Optional[str] = None):
    query = db.query(User)
    if status is not None and status != "":
        query = query.filter(User.status == status)
    if q:
        query = query.filter((User.nickname.contains(q)) | (User.email.contains(q)))
    users = query.all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "nickname": u.nickname,
            "is_admin": u.is_admin,
            "status": getattr(u, 'status', None)
        } for u in users
    ]

# 관리자 게시글 목록 API (검색/필터 지원)
@app.get("/api/admin/posts")
def admin_posts(db: Session = Depends(get_db), category: Optional[str] = None, q: Optional[str] = None):
    query = db.query(Post)
    if category is not None and category != "":
        query = query.filter(Post.category == category)
    if q:
        query = query.filter((Post.title.contains(q)) | (Post.content.contains(q)) | (Post.owner.has(User.nickname.contains(q))))
    posts = query.all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "category": p.category,
            "user_id": p.user_id,
            "nickname": p.owner.nickname if p.owner else None,
            "author": p.owner.nickname if p.owner else None,
            "created_at": p.created_at,
            "date": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else None,
            "is_notice": getattr(p, 'is_notice', 0)
        } for p in posts
    ]

# 관리자 게시글 삭제 API
@app.delete("/api/admin/posts/{post_id}")
def admin_delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return JSONResponse(status_code=404, content={"detail": "게시글이 없습니다."})
    db.delete(post)
    db.commit()
    return {"message": "게시글이 삭제되었습니다."}

# 관리자 회원 상태 변경 API
@app.patch("/api/admin/users/{user_id}/status")
def update_user_status(user_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    user.status = status
    db.commit()
    return {"message": f"사용자 상태가 '{status}'로 변경되었습니다."}

# 관리자 회원 활동 내역 조회 API
@app.get("/api/admin/users/{user_id}/activity")
def admin_user_activity(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "사용자를 찾을 수 없습니다."})
    posts = db.query(Post).filter(Post.user_id == user_id).order_by(Post.created_at.desc()).all()
    comments = db.query(Comment).filter(Comment.user_id == user_id).order_by(Comment.created_at.desc()).all()
    return {
        "nickname": user.nickname,
        "post_count": len(posts),
        "comment_count": len(comments),
        "posts": [
            {
                "id": p.id,
                "title": p.title,
                "category": p.category,
                "date": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else None
            } for p in posts
        ],
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "date": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else None,
                "post_id": c.post_id
            } for c in comments
        ]
    }
# --- 메뉴 월드컵(ideal) 라우터 등록 ---
app.include_router(ideal_router)


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, db: Session = Depends(get_db)):
    keyword = request.query_params.get("query") or request.query_params.get("keyword") or ''
    # 커뮤니티 카테고리(혼밥/데이트/기타/회식)만 검색
    valid_categories = ["혼밥", "데이트", "회식", "기타", "SOLO", "DATE", "WORK", "ETC"]
    # 제목, 내용, 카테고리, 작성자 닉네임에 keyword가 포함된 게시글만 필터
    posts = db.query(Post).join(User, Post.user_id == User.id)
    # 카테고리 한글/영문 혼합 허용, 혼밥/데이트/회식/기타만
    posts = posts.filter(
        Post.category.in_(valid_categories),
        (
            Post.title.contains(keyword) |
            Post.content.contains(keyword) |
            User.nickname.contains(keyword)
        ) if keyword else True
    ).order_by(Post.created_at.desc()).all()
    # 템플릿에 전달할 데이터 가공
    post_list = [
        {
            "id": p.id,
            "category": p.category,
            "title": p.title,
            "content": p.content,
            "nickname": p.owner.nickname if p.owner else "",
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            "comment_count": len(p.comments),
            "like_count": len(getattr(p, 'likes', [])) if hasattr(p, 'likes') else 0
        }
        for p in posts
    ]
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "keyword": keyword, "posts": post_list}
    )

from fastapi import Query

@app.get("/api/reverse-geocode")
def reverse_geocode(lat: float = Query(...), lon: float = Query(...)):
    # Kakao REST API로 역지오코딩
    KAKAO_REST_API_KEY = settings.KAKAO_REST_API_KEY
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"x": lon, "y": lat}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        logging.info(f'Kakao API 응답: {data}')
        # 주소 정보 파싱
        if data.get("documents"):
            doc = data["documents"][0]
            address = doc.get("address", {})
            road_address = doc.get("road_address", {})
            result = {
                "address": road_address.get("address_name") or address.get("address_name") or None,
                "building_name": road_address.get("building_name") or None
            }
            return result
        return {"address": None}
    except Exception as e:
        logging.error(f'Kakao API 에러: {e}')
        return {"error": str(e)}
