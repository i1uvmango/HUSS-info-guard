# Info-Guard 프로젝트

YouTube 영상의 신뢰도를 AI 기반으로 분석하는 플랫폼입니다.

## 🚀 주요 기능

- **AI 기반 신뢰도 분석**: 감정 분석, 편향 감지, 신뢰도 분석, 콘텐츠 분류
- **실시간 분석 진행상황**: WebSocket을 통한 실시간 모니터링
- **YouTube API 연동**: 영상 메타데이터, 자막, 댓글 자동 수집
- **배치 분석**: 여러 영상을 동시에 분석
- **RESTful API**: 표준 HTTP API 제공

## 🏗️ 프로젝트 구조

```
src/
├── python-server/          # AI 분석 서버 (FastAPI)
│   ├── api/
│   │   └── routers/
│   │       ├── health.py      # 헬스체크 API ✅
│   │       ├── analysis.py    # 분석 API ✅
│   │       └── websocket.py   # WebSocket API ✅
│   ├── ai_models/         # AI 모델들 ✅
│   ├── data_processing/   # 데이터 처리 모듈 ✅
│   ├── services/          # 비즈니스 로직 ✅
│   └── utils/             # 유틸리티 ✅
├── nodejs-server/         # 백엔드 API 서버 (Express.js)
└── chrome-extension/      # Chrome 확장 프로그램
```

## 🔧 기술 스택

### Backend
- **Python**: FastAPI, uvicorn
- **AI/ML**: scikit-learn, transformers, torch
- **Database**: PostgreSQL, Redis
- **Async**: asyncio, aiohttp

### Frontend
- **Chrome Extension**: JavaScript, HTML, CSS
- **Real-time**: WebSocket

## 📡 API 엔드포인트

### 분석 API (`/api/v1/analysis`)

#### 1. 영상 분석 요청
```http
POST /api/v1/analysis/analyze
```

**요청 본문:**
```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "analysis_types": ["sentiment", "bias", "credibility", "content"],
  "include_comments": true,
  "include_subtitles": true,
  "priority": "normal"
}
```

**응답:**
```json
{
  "analysis_id": "uuid",
  "status": "pending",
  "message": "분석이 시작되었습니다",
  "estimated_time_seconds": 45,
  "created_at": "2024-08-10T10:00:00Z"
}
```

#### 2. 분석 상태 조회
```http
GET /api/v1/analysis/status/{analysis_id}
```

**응답:**
```json
{
  "analysis_id": "uuid",
  "status": "processing",
  "progress": 40,
  "message": "AI 모델 분석 중...",
  "created_at": "2024-08-10T10:00:00Z",
  "updated_at": "2024-08-10T10:00:15Z"
}
```

#### 3. 분석 결과 조회
```http
GET /api/v1/analysis/result/{analysis_id}
```

**응답:**
```json
{
  "analysis_id": "uuid",
  "video_id": "VIDEO_ID",
  "video_title": "영상 제목",
  "overall_credibility_score": 0.75,
  "analysis_types": ["sentiment", "bias", "credibility"],
  "results": {
    "sentiment": {
      "label": "positive",
      "confidence": 0.8,
      "positive_score": 15,
      "negative_score": 3
    },
    "bias": {
      "label": "low_bias",
      "confidence": 0.7,
      "total_bias_score": 2
    },
    "credibility": {
      "label": "reliable",
      "credibility_score": 0.75,
      "factors": {
        "channel_credibility": 0.8,
        "content_quality": 0.9
      }
    }
  },
  "confidence_scores": {
    "sentiment": 0.8,
    "bias": 0.7,
    "credibility": 0.75
  },
  "analysis_time_seconds": 45.2,
  "created_at": "2024-08-10T10:00:00Z",
  "updated_at": "2024-08-10T10:00:45Z"
}
```

#### 4. 배치 분석
```http
POST /api/v1/analysis/batch
```

**요청 본문:**
```json
{
  "video_urls": [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.youtube.com/watch?v=VIDEO2"
  ],
  "analysis_types": ["sentiment", "credibility"],
  "max_concurrent": 3
}
```

#### 5. 분석 취소
```http
DELETE /api/v1/analysis/{analysis_id}
```

### WebSocket API (`/ws`)

#### 1. WebSocket 연결
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/ws/{client_id}');
```

#### 2. 분석 구독
```json
{
  "type": "subscribe_analysis",
  "analysis_id": "uuid"
}
```

#### 3. 실시간 메시지 타입

**분석 시작:**
```json
{
  "type": "analysis_started",
  "analysis_id": "uuid",
  "video_title": "영상 제목",
  "message": "분석이 시작되었습니다",
  "timestamp": "2024-08-10T10:00:00Z"
}
```

**분석 진행상황:**
```json
{
  "type": "analysis_progress",
  "analysis_id": "uuid",
  "progress": 40,
  "message": "AI 모델 분석 중...",
  "timestamp": "2024-08-10T10:00:15Z"
}
```

**분석 완료:**
```json
{
  "type": "analysis_completed",
  "analysis_id": "uuid",
  "result": {
    "video_title": "영상 제목",
    "overall_credibility_score": 0.75,
    "analysis_types": ["sentiment", "bias", "credibility"]
  },
  "message": "분석이 완료되었습니다",
  "timestamp": "2024-08-10T10:00:45Z"
}
```

**분석 실패:**
```json
{
  "type": "analysis_failed",
  "analysis_id": "uuid",
  "error": "오류 메시지",
  "message": "분석 중 오류가 발생했습니다",
  "timestamp": "2024-08-10T10:00:30Z"
}
```

#### 4. 연결 상태 조회
```http
GET /ws/connections/status
GET /ws/connections/user/{user_id}
GET /ws/connections/analysis/{analysis_id}
```

#### 5. WebSocket 테스트 페이지
```http
GET /ws/test
```

## 🚀 시작하기

### 1. 환경 설정
```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정값 입력
```

### 3. 데이터베이스 설정
```bash
# PostgreSQL 및 Redis 실행
docker-compose up -d postgres redis

# 데이터베이스 마이그레이션
python -m src.python-server.scripts.db_migrate
```

### 4. 서버 실행
```bash
# Python 서버 실행
python -m src.python-server.main

# 또는 직접 실행
cd src/python-server
python main.py
```

### 5. API 테스트
```bash
# 헬스체크
curl http://localhost:8000/health

# 분석 요청
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 6. WebSocket 테스트
브라우저에서 `http://localhost:8000/ws/test` 접속하여 WebSocket 기능 테스트

## 📊 분석 타입

### 1. 감정 분석 (Sentiment Analysis)
- **목적**: 영상 콘텐츠와 댓글의 감정적 톤 분석
- **출력**: positive/negative/neutral + 신뢰도 점수
- **데이터 소스**: 자막, 댓글, 제목, 설명

### 2. 편향 감지 (Bias Detection)
- **목적**: 정치적, 성별, 인종, 종교적 편향 감지
- **출력**: 편향 유형별 점수 + 전체 편향 정도
- **데이터 소스**: 자막, 댓글, 제목, 설명

### 3. 신뢰도 분석 (Credibility Analysis)
- **목적**: 영상의 전반적인 신뢰도 평가
- **출력**: 0-1 신뢰도 점수 + 세부 요인별 점수
- **고려 요소**: 채널 신뢰도, 콘텐츠 품질, 참여도, 댓글 품질

### 4. 콘텐츠 분류 (Content Classification)
- **목적**: 영상 콘텐츠의 카테고리 자동 분류
- **출력**: 주요 카테고리 + 신뢰도 점수
- **카테고리**: 뉴스, 교육, 엔터테인먼트, 기술, 라이프스타일 등

## 🔄 분석 워크플로우

1. **분석 요청**: 클라이언트가 YouTube URL과 분석 옵션 전송
2. **영상 정보 수집**: YouTube API를 통한 메타데이터, 자막, 댓글 수집
3. **AI 모델 분석**: 각 분석 타입별로 AI 모델 실행
4. **결과 통합**: 개별 분석 결과를 종합하여 전체 신뢰도 점수 계산
5. **실시간 알림**: WebSocket을 통한 진행상황 및 결과 전송
6. **결과 저장**: 데이터베이스에 분석 결과 저장

## 🧪 테스트

### API 테스트
```bash
# pytest 실행
pytest src/python-server/tests/

# 특정 테스트 실행
pytest src/python-server/tests/test_analysis.py -v
```

### WebSocket 테스트
1. 브라우저에서 `http://localhost:8000/ws/test` 접속
2. "연결" 버튼 클릭
3. 분석 ID 입력 후 "구독" 버튼 클릭
4. 다른 터미널에서 분석 요청 실행
5. 실시간 진행상황 확인

## 📈 성능 최적화

- **비동기 처리**: FastAPI의 비동기 특성 활용
- **백그라운드 작업**: 분석 작업을 백그라운드에서 실행
- **캐싱**: Redis를 통한 분석 결과 캐싱
- **배치 처리**: 여러 영상을 동시에 분석
- **연결 풀링**: 데이터베이스 및 외부 API 연결 재사용

## 🔒 보안

- **입력 검증**: Pydantic을 통한 요청 데이터 검증
- **에러 핸들링**: 상세한 에러 메시지 및 로깅
- **CORS 설정**: 허용된 도메인에서만 API 접근
- **Rate Limiting**: API 요청 제한 (구현 예정)

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.