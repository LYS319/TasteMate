# 🍶 TasteMate

> **사용자 입력·위치 기반 AI 주류/안주 추천 플랫폼**  
> SMU 2조 | 이윤성 · 박준영 · 채하율 · 황승민

---

## 📌 프로젝트 개요

TasteMate는 사용자의 자연어 질문, 현재 위치, 날씨 정보를 종합 분석하여  
AI가 주류와 안주 조합을 추천해주는 웹 플랫폼입니다.

- **슬로건:** 누구나 간편하게 유용한 정보를 얻을 수 있는 맞춤형 추천 시스템
- **핵심 차별점:** AI 추천 + 위치 연동 + 커뮤니티 RAG를 하나의 플랫폼에서 제공

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| **프론트엔드** | HTML / CSS / JavaScript (모바일 반응형) |
| **백엔드** | Python FastAPI (RESTful API + WebSocket) |
| **AI 추천** | Google Gemini 2.5 Flash (자연어 분석, RAG 반영) |
| **데이터베이스** | TiDB Cloud (MySQL 호환, 12개 테이블) |
| **지도 API** | 카카오맵 REST API + JavaScript SDK |
| **날씨 API** | 기상청 단기예보 API |
| **배포** | Cloudflare Tunnel (공인 HTTPS, GPS 지원) |
| **결제** | 토스페이먼츠 (빌링키 정기결제) |
| **실시간 통신** | WebSocket (FastAPI 내장, 1:1 채팅) |
| **버전 관리** | Git + GitHub (기능별 브랜치 전략) |

---

## 📁 프로젝트 구조

```
TasteMate/
├── main.py                  # FastAPI 앱 진입점 + 전체 API 라우터
├── Database.py              # SQLAlchemy 모델 정의 (12개 테이블)
├── config.py                # 환경변수 관리 (pydantic-settings)
├── requirements.txt         # 의존성 패키지
├── .env                     # 환경변수 (Git 제외)
├── create_tables.py         # DB 테이블 초기화 스크립트
├── friend-chat.js           # 친구 패널 & 실시간 채팅 공통 JS
├── _ad_banner.html          # 광고 배너 공통 템플릿 (Jinja2)
│
├── 테이스트메이트.html        # 메인 페이지 (/)
├── AICHAT.html              # AI 챗봇 추천 페이지 (/aichat)
├── COMMUNITY.html           # 커뮤니티 게시판 (/community)
├── WRITE.html               # 글쓰기 페이지 (/write)
├── post_detail.html         # 게시글 상세 페이지 (/post_detail/{id})
├── LOGIN.html               # 로그인 (/login)
├── SIGNUP.html              # 회원가입 (/signup)
├── MYPAGE.html              # 마이페이지 (/mypage)
├── MYPOSTS.html             # 내 게시글 목록
├── MYCONTENT.html           # 내 활동 내역
├── SOLO.html                # 카테고리 - 혼밥 (/SOLO)
├── DATE.html                # 카테고리 - 데이트 (/DATE)
├── WORK.html                # 카테고리 - 회식 (/WORK)
├── ETC.html                 # 카테고리 - 기타 (/ETC)
├── about.html               # 회사소개 (/about)
├── admin.html               # 관리자 페이지 (/admin)
├── search.html              # 검색 결과 (/search)
│
├── game_pinball.html        # 게임 - 핀볼 (/game/pinball)
├── game_ladder.html         # 게임 - 사다리타기 (/game/ladder)
├── game_random_amount.html  # 게임 - 룰렛/랜덤금액 (/game/random_amount)
├── game_worldcup.html       # 게임 - 음식 월드컵 (/game/worldcup)
└── game_calculator.html     # 게임 - 계산기 (/game/calculator)
```

---

## 🗄️ DB 설계 (TiDB Cloud)

| 테이블 | 설명 |
|--------|------|
| `users` | 사용자 기본 정보 (id, email, nickname, is_admin, status) |
| `posts` | 커뮤니티 게시글 (카테고리, 제목, 내용, 위치 정보, 공지 여부) |
| `comments` | 게시글 댓글 |
| `likes` | 게시글 좋아요 |
| `chat_history` | AI 챗봇 대화 기록 |
| `chat_messages` | 1:1 실시간 채팅 메시지 (WebSocket) |
| `friends` | 친구 관계 (user_id ↔ friend_id) |
| `friend_requests` | 친구 신청 (pending / accepted / rejected) |
| `user_logs` ★ | 사용자 행동 로그 (검색·추천·클릭) — MAU 분석용 |
| `user_profiles` ★ | AI 챗봇 추출 TASTE_DATA 취향 누적 — 개인화·B2B 판매용 |
| `location_logs` ★ | GPS 역지오코딩 결과 저장 — 상권 분석 리포트용 |

> ★ 수익화 전용 테이블 (B2B 데이터 판매·MAU 분석 활용)

---

## 🔌 API 설계

### 페이지 라우터

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/` | 루트 → 메인 리다이렉트 |
| GET | `/main` | 메인 페이지 |
| GET | `/aichat` | AI 챗봇 페이지 |
| GET | `/community` | 커뮤니티 게시판 |
| GET | `/write` | 글쓰기 페이지 |
| GET | `/post_detail/{post_id}` | 게시글 상세 |
| GET | `/SOLO` `/DATE` `/WORK` `/ETC` | 카테고리별 페이지 |
| GET | `/login` `/signup` `/mypage` | 인증·마이페이지 |
| GET | `/admin` | 관리자 페이지 |
| GET | `/about` | 회사소개 |
| GET | `/search` | 검색 결과 |
| GET | `/game/{type}` | 게임 페이지 5종 |

### AI / 추천 API

| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/chat` | AI 챗봇 메시지 처리 (Gemini + RAG) |
| POST | `/api/top-places` | 카카오맵 카테고리별 인기 장소 조회 |
| GET | `/api/weather` | 기상청 현재 날씨 조회 |
| GET | `/api/weather-recommend` | 날씨 기반 메뉴 추천 |
| GET | `/api/reverse-geocode` | GPS 좌표 → 주소 변환 |
| POST | `/api/user-profile` | 사용자 취향 프로필 저장 |

### 게시글 / 댓글 API

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/posts/{category}` | 카테고리별 게시글 목록 |
| GET | `/api/posts/detail/{post_id}` | 게시글 상세 + 댓글 |
| GET | `/api/posts/{category}/latest` | 최신순 게시글 |
| GET | `/api/posts/{category}/popular` | 인기순 게시글 |
| GET | `/api/posts/{category}/nearby` | 위치 기반 주변 게시글 |
| POST | `/api/posts` | 게시글 작성 |
| POST | `/api/posts/{post_id}/edit` | 게시글 수정 |
| POST | `/api/posts/{post_id}/delete` | 게시글 삭제 |
| POST | `/api/posts/{post_id}/like` | 좋아요 토글 |
| GET | `/api/posts/{post_id}/is_liked` | 좋아요 여부 확인 |
| POST | `/api/comments` | 댓글 등록 |

### 사용자 API

| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/login` | 로그인 |
| POST | `/api/signup` | 회원가입 |
| GET | `/api/users/{user_id}/me` | 내 정보 조회 |
| PATCH | `/api/users/{user_id}/nickname` | 닉네임 변경 |
| PATCH | `/api/users/{user_id}/password` | 비밀번호 변경 |
| PATCH | `/api/users/{user_id}/email` | 이메일 변경 |
| DELETE | `/api/users/{user_id}` | 회원 탈퇴 |
| POST | `/api/upload-image` | 이미지 업로드 |

### 친구 / 채팅 API

| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/friends/request` | 친구 신청 |
| GET | `/api/friends/status/{user_id}` | 친구 목록 + 수신 요청 조회 |
| POST | `/api/friends/action` | 친구 수락 / 거절 |
| POST | `/api/friends/delete` | 친구 삭제 |
| GET | `/api/chat/history` | 1:1 채팅 기록 조회 |
| WS | `/ws/chat/{user_id}` | WebSocket 실시간 채팅 |

### 관리자 API

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/admin/stats` | 전체 통계 (사용자·게시글·댓글 수) |
| GET | `/api/admin/users` | 회원 목록 (검색·필터) |
| GET | `/api/admin/posts` | 게시글 목록 (카테고리·검색) |
| DELETE | `/api/admin/users/{user_id}` | 회원 강제 탈퇴 |
| PATCH | `/api/admin/users/{user_id}/role` | 관리자 권한 변경 |
| PATCH | `/api/admin/users/{user_id}/status` | 회원 상태 변경 |
| DELETE | `/api/admin/posts/{post_id}` | 게시글 강제 삭제 |

---

## ⚙️ 시스템 아키텍처

```
사용자 (브라우저)
    ↕  HTTP / WebSocket
FastAPI 백엔드 (Python)
    ├─ Google Gemini 2.5 Flash API  →  AI 챗봇·RAG 추천
    ├─ 카카오맵 REST API            →  위치 기반 음식점 검색
    ├─ 기상청 단기예보 API          →  날씨 기반 추천
    └─ TiDB Cloud (MySQL)          →  사용자·커뮤니티·로그 DB
    ↕  Cloudflare Tunnel (공인 HTTPS)
외부 인터넷 (GPS·HTTPS 필수 기능 지원)
```

### AI 챗봇 RAG 흐름

```
사용자 질문 입력
    → 키워드 추출 (공백 분리)
    → TiDB posts 테이블 OR 검색 (title + content)
    → 관련 게시글 최대 3건 추출
    → system_prompt에 커뮤니티 컨텍스트 삽입
    → Gemini 2.5 Flash 응답 생성
    → TASTE_DATA JSON 파싱 → user_profiles 누적
    → 응답 반환
```

### WebSocket 실시간 채팅 흐름

```
연결: /ws/chat/{user_id}
    → 온라인: 즉시 전달
    → 오프라인: chat_messages DB 임시 저장
    → 재접속 시 /api/chat/history로 동기화
재연결: 지수 백오프 (3s → 6s → 12s → 24s → 30s 최대)
하트비트: 25초마다 ping 전송
```

---

## 🚀 로컬 실행 방법

### 1. 환경 설정

```bash
git clone https://github.com/your-repo/tastemate.git
cd tastemate
pip install -r requirements.txt
```

### 2. `.env` 파일 작성

```env
KAKAO_JAVAS_API_KEY=your_kakao_js_key
KAKAO_REST_API_KEY=your_kakao_rest_key
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_secret_key
ALGORITHM=HS256
TIDB_USER=your_tidb_user
TIDB_PASSWORD=your_tidb_password
TIDB_HOST=your_tidb_host
TIDB_PORT=4000
TIDB_DB_NAME=test
DATABASE_URL=mysql+pymysql://user:password@host:4000/test
```

### 3. DB 테이블 생성

```bash
python create_tables.py
```

### 4. 서버 실행

```bash
uvicorn main:app --host 192.x.x.x --port 8000 --reload
```

### 5. Cloudflare Tunnel (HTTPS + GPS 필요 시)

```bash
cloudflared tunnel --url http://192.x.x.x:8000
```

> 💡 GPS 기능은 HTTPS 환경에서만 동작합니다.  
> ngrok 무료 플랜은 경고 페이지 삽입 + 주소 변경 문제가 있어 Cloudflare Tunnel을 사용합니다.

---

## 💰 비즈니스 모델

| 수익 모델 | 내용 | 수금 방식 |
|-----------|------|-----------|
| ① 광고 수익 | 주류 브랜드·음식점 배너 노출 | 세금계산서 월정액 |
| ② 음식점 입점 등록비 | 가게 정보 등록 월정액 (수수료 없음) | 토스페이먼츠 카드·계좌이체 |
| ③ 프리미엄 구독 | 광고 제거 + AI 고급 추천 + 취향 리포트 | 토스페이먼츠 빌링키 정기결제 |
| ④ 데이터 판매 (B2B) | 익명화 소비 패턴·상권 분석 리포트 | API 과금 또는 단건 세금계산서 |

---

## 🎮 부가 기능

### 술자리 게임 5종
- 🎰 룰렛 게임 (`/game/random_amount`)
- 🪜 사다리타기 (`/game/ladder`)
- 🎯 핀볼 게임 (`/game/pinball`)
- 🏆 음식 월드컵 (`/game/worldcup`)
- 🧮 랜덤 금액 계산기 (`/game/calculator`)

### 실시간 기능
- WebSocket 1:1 채팅 + 친구 맺기
- GPS 위치 기반 주변 음식점 실시간 검색
- 날씨 연동 메뉴 추천

---

## 🔧 트러블슈팅 기록

| # | 문제 | 원인 | 해결책 |
|---|------|------|--------|
| 1 | Gemini API 응답 지연 | 응답 시간 불규칙 | 타임아웃 설정 + 안내 메시지 UX |
| 2 | TASTE_DATA 파싱 오류 | JSON 아닌 형식 반환 | 정규식 방어 코드 추가 |
| 3 | Git Merge Conflict | 동일 파일 동시 수정 | 기능별 브랜치 분리 + PR 리뷰 후 머지 |
| 4 | WebSocket 오프라인 메시지 유실 | 수신자 오프라인 | DB 임시 저장 → 재접속 시 동기화 |
| 5 | HTTPS 터널링 (ngrok → Cloudflare) | 경고 페이지 삽입·주소 매번 변경 | `cloudflared tunnel --url http://localhost:8000` |
| 6 | 기상청 API 좌표 변환 오류 | GPS→격자 변환 오차 | 공식 문서 기준 변환 함수 재작성 |
| 7 | 모바일 UI z-index 충돌 | position:fixed 요소 충돌 | 계층 명시 정의 + 광고 배너 하단 이동 |
| 8 | 카카오맵 Cloudflare 환경 미작동 | 도메인 미등록 | 카카오 개발자 콘솔에 Cloudflare 도메인 추가 |
| 9 | `kakao is not defined` 오류 | autoload=false 타이밍 문제 | `<script onload="onKakaoSDKLoad()">` 방식으로 전환 |
| 10 | Gemini API 호출 실패 (`google-generativeai` 누락) | requirements.txt 미등록 | `google-generativeai` 패키지 추가 |

---

## 📅 개발 일정

| 주차 | 내용 |
|------|------|
| 1주차 | 기획·요구사항 정의, 서비스 컨셉 확정, 역할 분담, 기술 스택 선정 |
| 2주차 | UI 설계·인터페이스 구성, 메인·커뮤니티·챗봇 화면, 프론트엔드 기반 구축 |
| 3주차 | AI 챗봇·위치·날씨·커뮤니티·게임 기능 구현, 백엔드 API 연동 |
| 4주차 | 통합 테스트, 모바일 UI 최적화, 발표 준비 |

---

## 👥 팀원 소개

| 이름 | 전공 | 담당 역할 |
|------|------|-----------|
| **이윤성** (팀장) | 컴퓨터 전자공학 | 프로젝트 기획 총괄, Git 브랜치 전략, Cloudflare Tunnel 배포, .env 환경 설정 |
| **채하율** | IT소프트웨어융합 | AI 챗봇 기획·개발, Gemini API 연동, TASTE_DATA 파싱, 커뮤니티 RAG 구현, 대화 기록 저장·관리 |
| **박준영** | 컴퓨터 전자공학 | 커뮤니티 게시판 CRUD, WebSocket 실시간 채팅, 오프라인 메시지 DB 동기화 |
| **황승민** | 전기전자 | FastAPI 백엔드 + TiDB DB 설계 (12개 테이블), 카카오맵·기상청 API 연동, 메인 홈 UI/UX, 모바일 반응형 CSS |

---

## 🔮 향후 개선 계획

- **모바일 앱 전환:** 반응형 웹 → React Native WebView 하이브리드 앱
- **이미지 추천 고도화:** Gemini Vision으로 음식 사진 → 주류·안주 조합 추천
- **취향 리포트:** 월간 소비 패턴 시각화 리포트 제공
- **예약 연계:** 제휴 매장 예약 기능 확장
- **서버 확장:** Docker → AWS EC2 / Cloud Run + Auto Scaling
- **시즌 콘텐츠:** 지역별·계절별 주류·안주 추천 큐레이션