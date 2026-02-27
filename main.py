import json
import requests
import logging
import random
import math
import datetime
from pydantic import BaseModel
from typing import List, Optional
from fastapi import FastAPI, Request, Depends, Form, HTTPException, File, UploadFile, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from starlette.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, text, func, desc
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from dotenv import load_dotenv
import os
import google.generativeai as genai
logging.basicConfig(level=logging.INFO)

from Database import Like, User, Post, Comment, Friend, ChatMessage, get_db
from config import settings
from game_ideal_router import router as ideal_router

app = FastAPI(title="Taste Mate Final System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

# =============================================
# WebSocket 연결 관리자
# =============================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[int(user_id)] = websocket
        logging.info(f"[WS] 연결됨: user_id={user_id}")

    def disconnect(self, user_id: int):
        uid = int(user_id)
        if uid in self.active_connections:
            del self.active_connections[uid]
            logging.info(f"[WS] 연결 종료: user_id={uid}")

    async def send_personal_message(self, message: dict, user_id: int):
        uid = int(user_id)
        if uid in self.active_connections:
            try:
                await self.active_connections[uid].send_json(message)
            except Exception as e:
                logging.error(f"[WS] 메시지 전송 실패: to={uid}, error={e}")
                self.disconnect(uid)
        else:
            logging.warning(f"[WS] 수신자 오프라인: user_id={uid}")

manager = ConnectionManager()


# --- 인기글 라우터 (AI 코드 건드리지 않음) ---
@app.get("/SOLO", response_class=HTMLResponse)
def solo_page(request: Request):
    return templates.TemplateResponse("SOLO.html", {"request": request})

@app.get("/DATE", response_class=HTMLResponse)
def date_page(request: Request):
    return templates.TemplateResponse("DATE.html", {"request": request})

@app.get("/WORK", response_class=HTMLResponse)
def work_page(request: Request):
    return templates.TemplateResponse("WORK.html", {"request": request})

@app.get("/ETC", response_class=HTMLResponse)
def etc_page(request: Request):
    return templates.TemplateResponse("ETC.html", {"request": request})

# --- Gemini AI 챗봇 엔드포인트 ---
class ChatRequest(BaseModel):
    message: str

# --- 카테고리별 인기 장소 API ---
from sqlalchemy import desc

# 🔥 카테고리별 인기 장소 요청 모델
class TopPlaceRequest(BaseModel):
    category: str
    lat: float
    lon: float


# 🔥 카테고리별 인기 장소 API (프론트와 구조 맞춤)
@app.post("/api/top-places")
def kakao_top_places(request: TopPlaceRequest):

    KAKAO_REST_API_KEY = settings.KAKAO_REST_API_KEY

    # 🔥 버튼별 검색 키워드 매핑
    keyword_map = {
        "혼밥": "혼밥 맛집",
        "데이트": "데이트 맛집",
        "술집": "술집"
    }

    keyword = keyword_map.get(request.category, request.category)

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }

    params = {
        "query": keyword,
        "x": request.lon,
        "y": request.lat,
        "radius": 2000,
        "size": 5
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        places = []

        for doc in data.get("documents", []):
            places.append({
                "name": doc.get("place_name"),
                "address": doc.get("road_address_name") or doc.get("address_name"),
                "map_url": doc.get("place_url")
            })

        return {"places": places}

    except Exception as e:
        logging.error(f"Kakao 장소 검색 에러: {e}")
        return {"places": []}

# ================================================================
# 이 파일의 내용을 main.py의 기존 /api/chat 엔드포인트와
# ChatRequest 모델을 아래 코드로 교체하세요.
# ================================================================

# --- 개선된 ChatRequest 모델 ---
class ChatRequest(BaseModel):
    message: str
    nickname: str = "손님"           # 사용자 닉네임
    history: list = []               # 이전 대화 내역 [{role, content}, ...]
    profile: dict = {}               # 취향 프로필 {preferred_alcohol, preferred_snack, situation, dislikes}
    situation: str = ""              # 현재 상황 (혼술/회식/데이트/기타)
    location: str = ""               # 현재 위치 (ex: 강남구 역삼동)
    current_hour: int = -1           # 현재 시각 (0~23), 시간대별 추천에 활용


# --- 개선된 /api/chat 엔드포인트 ---
@app.post("/api/chat")
async def chat(request: ChatRequest):
        # ============================
    # 🔎 RAG 1: 커뮤니티 게시글 검색
    # ============================
    from sqlalchemy import or_

    rag_context = ""

    try:
        db = next(get_db())

        # 사용자 질문을 단어 단위로 분리
        keywords = request.message.split()

        filters = []

        for word in keywords:
            if len(word) > 1:  # 한 글자 단어는 제외 (노이즈 방지)
                filters.append(Post.title.contains(word))
                filters.append(Post.content.contains(word))

        related_posts = (
            db.query(Post)
            .filter(or_(*filters))  # 여러 단어 OR 조건
            .order_by(Post.created_at.desc())
            .limit(3)
            .all()
        )

        if related_posts:
            rag_lines = []
            for p in related_posts:
                rag_lines.append(
                    f"- 제목: {p.title}\n  내용 요약: {p.content[:120]}"
                )

            rag_context = "\n".join(rag_lines)

    except Exception as e:
        logging.error(f"RAG 검색 에러: {e}")

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # ── 시간대 문구 ──
        hour = request.current_hour
        if 0 <= hour < 6:
            time_ctx = "새벽 시간대"
        elif 6 <= hour < 12:
            time_ctx = "오전"
        elif 12 <= hour < 17:
            time_ctx = "오후"
        elif 17 <= hour < 21:
            time_ctx = "저녁 황금시간대"
        else:
            time_ctx = "밤"

        # ── 취향 프로필 문자열 ──
        profile = request.profile
        profile_lines = []
        if profile.get("preferred_alcohol"):
            profile_lines.append(f"- 선호 주류: {profile['preferred_alcohol']}")
        if profile.get("preferred_snack"):
            profile_lines.append(f"- 선호 안주: {profile['preferred_snack']}")
        if profile.get("dislikes"):
            profile_lines.append(f"- 싫어하는 것: {profile['dislikes']}")
        if profile.get("situation"):
            profile_lines.append(f"- 주로 마시는 상황: {profile['situation']}")
        profile_str = "\n".join(profile_lines) if profile_lines else "아직 파악되지 않음"

        # ── 이전 대화 맥락 ──
        history_str = ""
        if request.history:
            recent = request.history[-6:]  # 최근 6턴만
            lines = []
            for h in recent:
                role_label = f"{request.nickname}" if h.get("role") == "user" else "AI"
                lines.append(f"{role_label}: {h.get('content', '')}")
            history_str = "\n".join(lines)

        # ── 상황 컨텍스트 ──
        situation_ctx = ""
        if request.situation == "혼술":
            situation_ctx = "혼자 조용히 마시는 혼술 상황입니다. 부담 없이 즐길 수 있는 추천을 해주세요."
        elif request.situation == "회식":
            situation_ctx = "여러 명이 함께하는 회식 자리입니다. 다양한 취향을 아우를 수 있는 추천을 해주세요."
        elif request.situation == "데이트":
            situation_ctx = "로맨틱한 데이트 상황입니다. 분위기 있는 술과 음식을 추천해주세요."
        elif request.situation:
            situation_ctx = f"'{request.situation}' 상황입니다."

        # ── 위치 컨텍스트 ──
        location_ctx = f"현재 위치: {request.location}" if request.location else ""

        # ── 시스템 프롬프트 ──
        community_context = rag_context if rag_context else "관련 커뮤니티 정보 없음"
        system_prompt = f"""
당신은 대한민국 최고의 주류·안주·맛집 전문 AI 소믈리에 '테이스트메이트'입니다.

[사용자 정보]
- 이름/닉네임: {request.nickname}
- 현재 시간대: {time_ctx}
{location_ctx}
{situation_ctx}

[커뮤니티 참고 정보 - 실제 사용자 후기]
{community_context}

[이전 대화 맥락]
{history_str if history_str else "첫 대화"}

[답변 스타일 - 매우 중요]

- 긴 설명형 문단을 작성하지 마세요.
- 각 추천은 "이름 + 한 줄 이유" 형식으로만 작성하세요.
- 불필요한 배경 설명은 생략하세요.
- 읽기 쉽게 줄바꿈을 사용하세요.
- 답변은 간결하고 리듬감 있게 작성하세요.

[답변 형식]

🍺 또는 🍷 추천 목록

1. [제품명]
→ [한 줄 이유]

2. [제품명]
→ [한 줄 이유]

3. [제품명]
→ [한 줄 이유]

💬 [친근한 코멘트 + 자연스러운 후속 질문]

---
[취향 추출 - 반드시 포함, JSON 형식, 답변 맨 끝에 숨겨서]
TASTE_DATA:{{
  "detected_alcohol": "[이번 대화에서 파악된 선호 주류, 없으면 null]",
  "detected_snack": "[이번 대화에서 파악된 선호 안주, 없으면 null]",
  "detected_dislike": "[이번 대화에서 파악된 기피 항목, 없으면 null]"
}}
"""

        # Gemini API 호출
        response = model.generate_content(system_prompt + f"\n\n{request.nickname}: {request.message}")

        raw_text = response.text

        # TASTE_DATA 추출 및 분리
        taste_data = {}
        display_text = raw_text
        if "TASTE_DATA:" in raw_text:
            parts = raw_text.split("TASTE_DATA:")
            display_text = parts[0].strip()
            try:
                import json
                import re
                json_str = re.search(r'\{.*?\}', parts[1], re.DOTALL)
                if json_str:
                    taste_data = json.loads(json_str.group())
            except Exception:
                pass

        return {
            "reply": display_text,
            "taste_data": taste_data  # 프론트에서 취향 프로필 업데이트에 사용
        }

    except Exception as e:
        logging.error(f"Gemini 에러: {e}")
        return {"reply": "AI 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.", "taste_data": {}}


# ================================================================
# 취향 프로필 온보딩 API (신규 유저 첫 접속 시)
# ================================================================
class ProfileRequest(BaseModel):
    preferred_alcohol: str = ""
    preferred_snack: str = ""
    dislikes: str = ""
    situation: str = ""

@app.post("/api/user-profile")
async def save_user_profile(profile: ProfileRequest):
    """
    프론트에서 localStorage에 저장하는 방식이므로,
    이 엔드포인트는 서버 측 검증/응답용으로 활용.
    실제 저장은 프론트 localStorage에서 처리.
    """
    return {"message": "프로필 저장 완료", "profile": profile.dict()}

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

# 위치 기반 근처 게시글 (하버사인 공식)
@app.get("/api/posts/{category}/nearby")
def get_posts_nearby(
    category: str,
    lat: float = Query(...),
    lon: float = Query(...),
    radius: float = Query(5.0),  # km 단위, 기본 5km
    db: Session = Depends(get_db)
):
    import math

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    # 위치 정보 있는 글만 조회
    posts = db.query(Post).filter(
        Post.category == category.upper(),
        Post.lat != None,
        Post.lon != None
    ).order_by(Post.is_notice.desc(), Post.created_at.desc()).all()

    nearby = []
    for post in posts:
        dist = haversine(lat, lon, post.lat, post.lon)
        if dist <= radius:
            nearby.append({
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "nickname": post.owner.nickname if post.owner else "",
                "created_at": post.created_at,
                "comment_count": len(post.comments),
                "like_count": len(getattr(post, 'likes', [])) if hasattr(post, 'likes') else 0,
                "is_notice": getattr(post, 'is_notice', 0),
                "distance": round(dist, 2),
                "place_name": getattr(post, 'place_name', None),
            })

    # 거리순 정렬 (공지는 맨 위)
    nearby.sort(key=lambda x: (x['is_notice'] == 0, x['distance']))
    return nearby
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

    KAKAO_REST_API_KEY = settings.KAKAO_REST_API_KEY
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"x": lon, "y": lat}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        logging.info(f"Kakao API 응답: {data}")

        # documents가 존재할 때만 처리
        if "documents" in data and len(data["documents"]) > 0:
            doc = data["documents"][0]
            address = doc.get("address", {})

            region1 = address.get("region_1depth_name", "")
            region2 = address.get("region_2depth_name", "")
            region3 = address.get("region_3depth_name", "")

            short_address = " ".join(
                [r for r in [region1, region2, region3] if r]
            )

            return {"address": short_address}

        # documents 없을 경우
        return {"address": None}

    except Exception as e:
        logging.error(f"Kakao API 에러: {e}")
        return {"address": None}

# =============================================
# 날씨별 음식 추천 (기상청 초단기실황 API)
# =============================================
@app.get("/api/weather")
async def get_weather(lat: float = Query(...), lon: float = Query(...)):
    return await get_weather_recommendation(lat, lon)

@app.get("/api/weather-recommend")
async def get_weather_recommendation(lat: float = Query(...), lon: float = Query(...)):

    def dfs_xy_conv(lat, lon):
        RE, GRID = 6371.00877, 5.0
        SLAT1, SLAT2, OLON, OLAT, XO, YO = 30.0, 60.0, 126.0, 38.0, 43, 136
        DEGRAD = math.pi / 180.0
        re = RE / GRID
        slat1, slat2 = SLAT1 * DEGRAD, SLAT2 * DEGRAD
        olon, olat = OLON * DEGRAD, OLAT * DEGRAD
        sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
            math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5))
        sf = math.pow(math.tan(math.pi * 0.25 + slat1 * 0.5), sn) * math.cos(slat1) / sn
        ro = re * sf / math.pow(math.tan(math.pi * 0.25 + olat * 0.5), sn)
        ra = re * sf / math.pow(math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5), sn)
        theta = (lon * DEGRAD - olon) * sn
        if theta > math.pi: theta -= 2.0 * math.pi
        if theta < -math.pi: theta += 2.0 * math.pi
        return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)

    # ── 1. 기상청 초단기실황 API 호출 (기온/습도/바람/강수/하늘) ──
    weather_info = {"temp": 20.0, "humidity": 50, "wind": 0.0, "rain": 0.0, "sky": "맑음"}
    try:
        from urllib.parse import unquote
        x, y = dfs_xy_conv(lat, lon)
        now = datetime.datetime.now()
        base_dt = now - datetime.timedelta(hours=1) if now.minute < 40 else now
        url = (
            f'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
            f'?serviceKey={unquote(settings.KMA_API_KEY)}&numOfRows=20&pageNo=1&dataType=JSON'
            f'&base_date={now.strftime("%Y%m%d")}&base_time={base_dt.strftime("%H00")}&nx={x}&ny={y}'
        )
        resp = requests.get(url, timeout=5)
        logging.info(f"[날씨] 기상청 status={resp.status_code}, nx={x}, ny={y}")

        if resp.ok:
            sky_code = {"1": "맑음", "3": "구름 많음", "4": "흐림"}
            pty_code  = {"0": "", "1": "비", "2": "비/눈", "3": "눈", "5": "빗방울", "6": "빗방울/눈날림", "7": "눈날림"}
            items = resp.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            pty_val = ""
            for item in items:
                cat, val = item.get('category'), str(item.get('obsrValue', ''))
                if cat == 'T1H':  weather_info['temp']     = float(val)
                elif cat == 'REH': weather_info['humidity'] = int(float(val))
                elif cat == 'WSD': weather_info['wind']     = float(val)
                elif cat == 'RN1': weather_info['rain']     = float(val) if val != '강수없음' else 0.0
                elif cat == 'SKY': weather_info['sky']      = sky_code.get(val, '맑음')
                elif cat == 'PTY': pty_val = pty_code.get(val, '')
            if pty_val:
                weather_info['sky'] = pty_val  # 강수 있으면 sky 덮어쓰기
            logging.info(f"[날씨] 수신 완료: {weather_info}")
    except Exception as e:
        logging.warning(f"[날씨] 기상청 API 실패, 기본값 사용: {e}")

    # ── 2. Gemini AI 메뉴 추천 ──
    try:
        temp     = weather_info['temp']
        humidity = weather_info['humidity']
        wind     = weather_info['wind']
        rain     = weather_info['rain']
        sky      = weather_info['sky']
        now_hour = datetime.datetime.now().hour
        meal_time = "아침" if now_hour < 10 else "점심" if now_hour < 15 else "저녁" if now_hour < 21 else "야식"

        # 매 요청마다 다른 추천을 위한 랜덤 힌트
        food_styles = ["한식", "분식", "일식", "중식", "양식", "국물요리", "면요리", "구이", "찜/조림", "디저트/음료"]
        avoid_hint = random.choice(food_styles)
        seed = random.randint(1, 9999)

        prompt = f"""당신은 날씨와 음식을 잘 아는 한국 맛집 전문가입니다.
지금 날씨 정보:
- 기온: {temp}℃
- 날씨: {sky}
- 습도: {humidity}%
- 바람: {wind}m/s
- 강수량: {rain}mm
- 식사 시간대: {meal_time}
- 추천 번호: {seed}번째 추천 (매번 반드시 다른 음식을 추천할 것)
- 이번엔 "{avoid_hint}" 계열 외의 음식을 우선 고려해주세요

이 날씨와 시간대에 잘 어울리는 한국 음식 1가지를 추천하고, 왜 이 날씨에 어울리는지 한 줄로 설명해주세요.
절대 매번 같은 음식을 추천하지 마세요. 다양한 음식 중에서 오늘 날씨에 맞는 것을 골라주세요.

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트는 절대 포함하지 마세요:
{{
  "title": "날씨를 표현하는 짧은 제목 (이모지 포함, 15자 이내)",
  "menu": "추천 메뉴 1개",
  "reason": "이 날씨에 이 음식이 어울리는 이유 (1문장, 30자 이내)",
  "search": "추천 메뉴 1개",
  "tag": "#해시태그"
}}"""

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"temperature": 1.8, "top_p": 0.95, "top_k": 64}
        )
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()

        import json
        result = json.loads(raw)
        result["title"] = f"{result['title']} ({temp}℃)"
        logging.info(f"[날씨] Gemini 추천 완료: {result.get('menu')}")
        return result

    except Exception as e:
        logging.error(f"[날씨] Gemini 추천 실패: {e}", exc_info=True)
        temp = weather_info['temp']
        if temp <= 0:    title, menu, reason = "🥶 꽁꽁 얼어붙는 추위", "감자탕", "칼바람 부는 날엔 뜨끈한 국물이 최고예요"
        elif temp <= 10: title, menu, reason = "🧥 쌀쌀한 날씨", "부대찌개", "쌀쌀한 날씨엔 얼큰하고 든든한 한 끼가 필요해요"
        elif temp <= 20: title, menu, reason = "🌤️ 기분 좋은 날씨", "비빔밥", "선선한 날씨에 가볍고 균형 잡힌 비빔밥 어떠세요"
        elif temp <= 28: title, menu, reason = "☀️ 따뜻한 날씨", "냉면", "더위가 오기 전 시원한 냉면으로 기분 전환해요"
        else:            title, menu, reason = "🥵 숨막히는 폭염", "팥빙수", "이 더위엔 달콤한 팥빙수 한 그릇이 답이에요"
        return {
            "title": f"{title} ({temp}℃)",
            "menu": menu,
            "reason": reason,
            "search": menu,
            "tag": "#오늘의메뉴"
        }


# =============================================
# 친구 API
# =============================================
@app.post("/api/friends/request")
async def friend_request(nickname: str = Form(...), from_user: int = Form(...), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.nickname == nickname).first()
    if not target:
        return JSONResponse(status_code=404, content={"message": "닉네임을 다시 확인해주세요."})
    if target.id == int(from_user):
        return JSONResponse(status_code=400, content={"message": "본인에게는 신청할 수 없습니다."})
    already_friend = db.query(Friend).filter(
        (((Friend.user_id == from_user) & (Friend.friend_id == target.id)) |
         ((Friend.user_id == target.id) & (Friend.friend_id == from_user))) &
        (Friend.status == "accepted")
    ).first()
    if already_friend:
        return JSONResponse(status_code=400, content={"message": "이미 친구 관계입니다."})
    already_pending = db.query(Friend).filter(
        (((Friend.user_id == from_user) & (Friend.friend_id == target.id)) |
         ((Friend.user_id == target.id) & (Friend.friend_id == from_user))) &
        (Friend.status == "pending")
    ).first()
    if already_pending:
        return JSONResponse(status_code=400, content={"message": "이미 친구 신청을 보냈거나 받은 상태입니다."})
    new_req = Friend(user_id=int(from_user), friend_id=target.id, status="pending")
    db.add(new_req)
    db.commit()
    return {"message": f"{nickname}님에게 친구신청이 완료됐습니다!"}

@app.get("/api/friends/status/{user_id}")
async def get_friends_status(user_id: int, db: Session = Depends(get_db)):
    friends_rows = db.query(Friend).filter(
        ((Friend.user_id == user_id) | (Friend.friend_id == user_id)) & (Friend.status == "accepted")
    ).all()
    friend_ids = [f.friend_id if f.user_id == user_id else f.user_id for f in friends_rows]
    friend_users = db.query(User).filter(User.id.in_(friend_ids)).all() if friend_ids else []
    pending_rows = db.query(Friend).filter(Friend.friend_id == user_id, Friend.status == "pending").all()
    request_list = []
    for row in pending_rows:
        sender = db.query(User).filter(User.id == row.user_id).first()
        if sender:
            request_list.append({"id": sender.id, "nickname": sender.nickname})
    return {
        "friends": [{"id": u.id, "nickname": u.nickname} for u in friend_users],
        "requests": request_list
    }

@app.post("/api/friends/action")
async def friend_action(
    user_id: int = Form(...), target_id: int = Form(...), action: str = Form(...),
    db: Session = Depends(get_db)
):
    req = db.query(Friend).filter(
        Friend.user_id == target_id, Friend.friend_id == user_id, Friend.status == "pending"
    ).first()
    if not req:
        return JSONResponse(status_code=404, content={"message": "친구 요청을 찾을 수 없습니다."})
    if action == "accept":
        req.status = "accepted"; db.commit()
        return {"message": "친구 요청을 수락했습니다."}
    elif action == "reject":
        db.delete(req); db.commit()
        return {"message": "친구 요청을 거절했습니다."}
    return JSONResponse(status_code=400, content={"message": "잘못된 action입니다."})

@app.post("/api/friends/delete")
async def delete_friend(user_id: int = Form(...), friend_id: int = Form(...), db: Session = Depends(get_db)):
    deleted = db.query(Friend).filter(
        (((Friend.user_id == user_id) & (Friend.friend_id == friend_id)) |
         ((Friend.user_id == friend_id) & (Friend.friend_id == user_id))) &
        (Friend.status == "accepted")
    ).all()
    if not deleted:
        return JSONResponse(status_code=404, content={"message": "친구 관계를 찾을 수 없습니다."})
    for row in deleted:
        db.delete(row)
    db.commit()
    return {"message": "친구를 삭제했습니다."}


# =============================================
# 채팅 API & WebSocket
# =============================================
@app.get("/api/chat/history")
async def get_chat_history(user1: int, user2: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(
        ((ChatMessage.sender_id == user1) & (ChatMessage.receiver_id == user2)) |
        ((ChatMessage.sender_id == user2) & (ChatMessage.receiver_id == user1))
    ).order_by(ChatMessage.created_at.asc()).all()
    return [{"sender_id": m.sender_id, "message": m.message} for m in messages]

@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    db = next(get_db())
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
            except json.JSONDecodeError:
                continue
            msg_type = msg_data.get('type', '')
            if msg_type in ('ping', 'pong', 'typing'):
                continue
            receiver_id  = int(msg_data.get('receiver_id', 0))
            message_text = msg_data.get('message', '').strip()
            if not receiver_id or not message_text:
                continue
            new_msg = ChatMessage(sender_id=user_id, receiver_id=receiver_id, message=message_text)
            db.add(new_msg)
            db.commit()
            await manager.send_personal_message(
                {"sender_id": user_id, "receiver_id": receiver_id, "message": message_text},
                receiver_id
            )
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logging.error(f"[WS] 예외: user_id={user_id}, error={e}")
        manager.disconnect(user_id)