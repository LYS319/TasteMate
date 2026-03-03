# 🍶 TasteMate

> AI 기반 맞춤형 주류·안주 추천 플랫폼  
> 사용자의 취향·상황·위치를 분석해 최적의 조합을 제안하고, 실제 방문까지 연결하는 통합 서비스

---

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | TasteMate (테이스트메이트) |
| 팀원 | 이윤성(팀장), 박준영, 채하율, 황승민 |
| 스택 | Python · FastAPI · SQLite · Gemini AI · KMA API · Kakao Map API · WebSocket |
| 배포 | uvicorn + ngrok (로컬 개발) |
| 서버 | `uvicorn main:app --host 192.168.0.239 --port 8000` |

---

## 🚀 주요 기능

### 1. AI 소믈리에 챗봇 (RAG 기반 취향 학습)
- 자연어로 질문하면 Gemini AI가 주류·안주 TOP3 추천
- 커뮤니티 게시글을 실시간 검색해 참고하는 **RAG(검색 증강 생성)** 방식 적용
- 상황(혼술 / 회식 / 데이트 / 기타), 현재 위치, 이전 대화 히스토리 반영
- 대화 중 파악된 취향(선호 주류·안주·기피 항목)을 프로필에 자동 누적
- 첫 접속 시 **취향 온보딩 모달**로 초기 프로필 설정

### 2. 날씨 기반 AI 메뉴 추천
- **기상청 초단기실황 API** 연동 (기온·날씨·습도·강수량 실시간 수집)
- 위경도 → 격자 좌표 변환 (`dfs_xy_conv`) 직접 구현
- Gemini가 날씨·시간대에 맞는 한국 음식 메뉴를 매번 다르게 추천 (temperature=1.8)
- 메인 화면 날씨 카드 클릭 → 네이버 지도 맛집 검색 연결
- API 실패 시 기온 기반 폴백 메뉴 자동 반환

### 3. 위치 기반 장소 추천
- Kakao Map API로 주변 음식점·주류 판매처 검색
- 하버사인(Haversine) 공식으로 반경 내 게시글 필터링
- 거리 + 평점 복합 점수 정렬 알고리즘 적용
- 카테고리별 조회 (SOLO / DATE / WORK / ETC)

### 4. 커뮤니티
- 카테고리별 게시글 작성·조회·수정·삭제
- 좋아요 / 댓글 / 대댓글 기능
- 근처 게시글 필터 (현재 위치 기준)
- 신고 기능 (`/report`)
- 게시글 검색 (`/search`)

### 5. 친구 맺기 & 실시간 채팅
- 닉네임 검색으로 친구 추가 / 요청 수락·거절·삭제
- **WebSocket 기반 실시간 채팅** (최대 5개 창 동시 운영)
- 모든 페이지 우측 하단 💬 FAB 버튼으로 어디서든 접근
- 대화 내역 DB 저장 → 재접속 시 히스토리 유지 (`/api/chat/history`)

### 6. 광고 배너 (수익 모델)
- PC 우측 사이드 배너 + 모바일 상단 배너 구현 (`_ad_banner.html`)
- 실제 광고 연동 시 즉시 수익화 가능한 구조

### 7. 관리자 페이지
- 회원 목록 조회 및 관리
- 게시글 통계 대시보드
- 신고 내역 처리 (`/admin`)

---

## 🗂️ 파일 구조

```
TasteMate/
├── main.py                  # FastAPI 서버 (전체 API 엔드포인트)
├── Database.py              # SQLAlchemy 모델 (User, Post, Comment, Friend, ChatMessage 등)
├── config.py                # 환경변수 설정 (API 키)
├── migrate_add_store_columns.py  # DB 마이그레이션 스크립트
│
├── MAIN.html                # 메인 페이지 (날씨 카드, 네비게이션)
├── AICHAT.html              # AI 소믈리에 챗봇 (취향 온보딩, 히스토리 패널)
├── COMMUNITY.html           # 커뮤니티 피드
├── WRITE.html               # 게시글 작성
├── post_detail.html         # 게시글 상세
├── MYPAGE.html              # 마이페이지
├── MYPOSTS.html             # 내 게시글
├── MYCONTENT.html           # 내 활동 내역
├── SIGNUP.html / LOGIN.html # 회원가입·로그인
├── about.html               # 서비스 소개
├── search.html              # 검색
├── admin.html               # 관리자 페이지
│
├── SOLO.html                # 카테고리 - 혼술
├── DATE.html                # 카테고리 - 데이트
├── WORK.html                # 카테고리 - 회식
├── ETC.html                 # 카테고리 - 기타
│
├── game_calculator.html     # 술자리 계산기 미니게임
├── game_ladder.html         # 사다리 게임
├── game_pinball.html        # 핀볼 게임
├── game_worldcup.html       # 월드컵 게임
├── game_random_amount.html  # 랜덤 금액 게임
│
├── _ad_banner.html          # 광고 배너 컴포넌트
├── friend-chat.js           # 친구 채팅 클라이언트 (WebSocket)
│
├── cert.pem / key.pem       # SSL 인증서 (ngrok HTTPS)
└── 테이스트메이트.html       # 랜딩 페이지
```

---

## ⚙️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install fastapi uvicorn sqlalchemy python-jose passlib python-multipart aiofiles google-generativeai httpx
```

### 2. 환경변수 설정 (`config.py`)

```python
GEMINI_API_KEY = "your_gemini_api_key"
KAKAO_REST_API_KEY = "your_kakao_rest_api_key"
KMA_API_KEY = "your_kma_api_key"
SECRET_KEY = "your_jwt_secret"
```

### 3. DB 초기화 및 마이그레이션

```bash
python Database.py          # 초기 테이블 생성
python migrate_add_store_columns.py  # 장소 컬럼 추가
```

### 4. 서버 실행

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. ngrok 터널 (외부 접속용)

```bash
ngrok http 8000
```

> ⚠️ ngrok 주소가 바뀔 때마다 `config.py`의 Kakao CORS 허용 도메인을 업데이트해야 합니다.

---

## 🔌 주요 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat` | AI 챗봇 (RAG + 취향 학습) |
| GET | `/api/weather` | 현재 날씨 조회 |
| GET | `/api/weather-recommend` | 날씨 기반 메뉴 추천 |
| GET | `/api/reverse-geocode` | 위경도 → 주소 변환 |
| GET | `/api/top-places` | 카테고리별 주변 장소 |
| GET | `/api/posts/{category}/nearby` | 근처 게시글 |
| POST | `/api/friends/request` | 친구 요청 |
| GET | `/api/friends/status` | 친구 상태 조회 |
| POST | `/api/friends/action` | 친구 요청 수락/거절 |
| DELETE | `/api/friends/delete` | 친구 삭제 |
| GET | `/api/chat/history` | 채팅 내역 조회 |
| WS | `/ws/chat/{user_id}` | 실시간 WebSocket 채팅 |
| POST | `/api/user-profile` | 취향 프로필 업데이트 |

---

## 🐛 트러블슈팅 기록

### 1. Gemini API 응답 지연 & Rate Limit
- **문제**: 동시 접속 시 날씨 추천 카드 로딩 5초+ 지연
- **해결**: 기온 기반 폴백 메뉴 하드코딩, API 실패 시 자동 전환
- **예정**: 동일 조건 응답 30분 캐싱

### 2. AI 챗봇 TASTE_DATA 파싱 오류
- **문제**: Gemini 응답에 마크다운 코드블록(` ```json `)이 섞여 JSON 파싱 실패
- **해결**: `re.search`로 JSON 블록만 추출, 실패 시 빈 딕셔너리로 대체
- **예정**: 프롬프트 강화 + 응답 검증 로직 보강

### 3. Git 충돌 (main.py Merge Conflict)
- **문제**: 팀원 기능 병합 시 `<<<<<<< HEAD` 마커 잔존 → FastAPI SyntaxError
- **해결**: ConnectionManager(기존)와 RAG 챗봇(팀원) 코드 수동 병합
- **예정**: 기능별 브랜치 분리 + PR 리뷰 규칙 도입

### 4. WebSocket 오프라인 메시지 유실
- **문제**: 수신자 오프라인 시 실시간 전송 불가 → 메시지 미도달
- **해결**: 모든 메시지 DB 저장 후 `GET /api/chat/history`로 재조회
- **예정**: 미확인 메시지 뱃지 표시

### 5. ngrok 브라우저 경고 & 주소 만료
- **문제**: 재시작마다 URL 변경 → Kakao CORS 재등록, 경고 페이지 반복
- **해결**: FastAPI 미들웨어에 `ngrok-skip-browser-warning` 헤더 자동 추가
- **예정**: 고정 도메인 운영 (ngrok 유료 또는 클라우드 배포)

### 6. 기상청 API 좌표 변환 오류
- **문제**: GPS 좌표 직접 사용 시 "기상 데이터 없음" 오류
- **해결**: 람베르트 정각원추 투영법 기반 `dfs_xy_conv()` 함수 직접 구현
- **비고**: API 실패 시에도 기온 기반 폴백 메뉴 반환

### 7. 모바일 z-index 충돌 (버튼 가림)
- **문제**: AICHAT 히스토리 패널(z-index 2500)이 💬 FAB(z-index 2001) 덮음
- **해결**: FAB → 2600, 패널 → 2602로 재정렬 / COMMUNITY 글쓰기 버튼 `right:110px` 이동

---

## 🗓️ 개발 일정

| 주차 | 내용 |
|------|------|
| 1주차 | 기획, DB 설계, 기본 인증(로그인·회원가입) |
| 2주차 | UI 구성, 커뮤니티, 카테고리 페이지 |
| 3주차 | AI 챗봇(RAG), 날씨 추천, 친구·채팅, 관리자 |
| 4주차 | 모바일 반응형, 버그 수정, 테스트, 최종 정리 |

---

## 👥 팀원 역할

| 이름 | 역할 |
|------|------|
| 이윤성 | 팀장 · 전체 기획 · 백엔드 통합 · AI 챗봇 · 날씨 추천 |
| 박준영 | 기능 기획 · 개발 협업 · 브레인스토밍 |
| 채하율 | 기능 기획 · RAG 챗봇 · UI 개발 |
| 황승민 | 기능 기획 · 개발 협업 · 테스트 |

---

## 📎 참고 API

- [Google Gemini API](https://ai.google.dev/)
- [Kakao Map API](https://developers.kakao.com/)
- [기상청 초단기실황 API](https://www.data.go.kr/)