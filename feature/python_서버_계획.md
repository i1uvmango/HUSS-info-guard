# Python 서버 구현 계획

## 🎯 **Python 서버 개요**
Info-Guard Python 서버는 AI 모델을 통한 YouTube 영상 신뢰도 분석의 핵심 역할을 담당합니다. FastAPI 기반으로 구축되어 실시간 분석과 WebSocket 통신을 지원합니다.

## 🏗️ **아키텍처 구조**

### 1. 디렉토리 구조
```
src/python-server/
├── main.py                    # 메인 서버 진입점
├── app/                       # 애플리케이션 핵심
│   ├── __init__.py
│   ├── core/                  # 핵심 설정 및 유틸리티
│   │   ├── __init__.py
│   │   ├── config.py          # 설정 관리
│   │   ├── logging.py         # 로깅 시스템
│   │   └── exceptions.py      # 커스텀 예외 클래스
│   ├── api/                   # API 레이어
│   │   ├── __init__.py
│   │   ├── deps.py            # 의존성 주입
│   │   ├── middleware.py      # 미들웨어
│   │   └── v1/                # API 버전 1
│   │       ├── __init__.py
│   │       ├── health.py      # 헬스체크
│   │       ├── analysis.py    # 분석 API
│   │       └── websocket.py   # WebSocket
│   ├── models/                # 데이터 모델
│   │   ├── __init__.py
│   │   ├── analysis.py        # 분석 관련 모델
│   │   ├── youtube.py         # YouTube 관련 모델
│   │   └── common.py          # 공통 모델
│   ├── services/              # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── analysis.py        # 분석 서비스
│   │   ├── youtube.py         # YouTube 서비스
│   │   ├── ai_models.py       # AI 모델 서비스
│   │   └── cache.py           # 캐시 서비스
│   ├── ai/                    # AI 모델
│   │   ├── __init__.py
│   │   ├── base.py            # 기본 모델 클래스
│   │   ├── sentiment.py       # 감정 분석
│   │   ├── bias.py            # 편향 감지
│   │   ├── credibility.py     # 신뢰도 분석
│   │   └── classifier.py      # 콘텐츠 분류
│   └── utils/                 # 유틸리티
│       ├── __init__.py
│       ├── text.py            # 텍스트 처리
│       └── validators.py      # 검증 유틸리티
├── tests/                     # 테스트 코드
├── requirements.txt            # 의존성 패키지
└── Dockerfile                 # Docker 설정
```

## 🚀 **구현 단계별 계획**

### **1단계: 기본 구조 및 설정**

#### 1.1 메인 서버 파일 (`main.py`)
```python
# 구현 위치: src/python-server/main.py
# 구현 함수: create_app(), start_server()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import health, analysis, websocket

def create_app():
    app = FastAPI(
        title="Info-Guard AI Analysis Server",
        description="YouTube 영상 신뢰도 분석 AI 서버",
        version="1.0.0"
    )
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API 라우터 등록
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 1.2 설정 관리 (`app/core/config.py`)
```python
# 구현 위치: src/python-server/app/core/config.py
# 구현 클래스: Settings

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "chrome-extension://*"]
    
    # YouTube API 설정
    YOUTUBE_API_KEY: str
    
    # AI 모델 설정
    MODEL_PATH: str = "./models"
    GPU_ENABLED: bool = True
    
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://user:password@localhost/info_guard"
    REDIS_URL: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### **2단계: AI 모델 구현**

#### 2.1 기본 AI 모델 클래스 (`app/ai/base.py`)
```python
# 구현 위치: src/python-server/app/ai/base.py
# 구현 클래스: BaseAIModel

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import torch
import numpy as np

class BaseAIModel(ABC):
    def __init__(self, model_path: str, device: str = "auto"):
        self.model_path = model_path
        self.device = self._get_device(device)
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _get_device(self, device: str) -> str:
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    @abstractmethod
    def _load_model(self):
        """모델 로드 구현"""
        pass
    
    @abstractmethod
    def predict(self, text: str) -> Dict[str, Any]:
        """예측 수행 구현"""
        pass
    
    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        return text.strip().lower()
    
    def postprocess_output(self, output: Any) -> Dict[str, Any]:
        """출력 후처리"""
        return {"result": output}
```

#### 2.2 감정 분석 모델 (`app/ai/sentiment.py`)
```python
# 구현 위치: src/python-server/app/ai/sentiment.py
# 구현 클래스: SentimentAnalyzer

from .base import BaseAIModel
from transformers import pipeline
from typing import Dict, Any

class SentimentAnalyzer(BaseAIModel):
    def _load_model(self):
        """감정 분석 모델 로드"""
        self.analyzer = pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
            device=0 if self.device == "cuda" else -1
        )
    
    def predict(self, text: str) -> Dict[str, Any]:
        """감정 분석 수행"""
        processed_text = self.preprocess_text(text)
        result = self.analyzer(processed_text)
        
        # 감정 점수 계산 (1-5 스케일을 0-100으로 변환)
        score = float(result[0]['label'].split()[0]) * 20
        
        return {
            "sentiment_score": score,
            "sentiment_label": result[0]['label'],
            "confidence": result[0]['score'],
            "text": text
        }
```

#### 2.3 편향 감지 모델 (`app/ai/bias.py`)
```python
# 구현 위치: src/python-server/app/ai/bias.py
# 구현 클래스: BiasDetector

from .base import BaseAIModel
from transformers import pipeline
from typing import Dict, Any, List

class BiasDetector(BaseAIModel):
    def _load_model(self):
        """편향 감지 모델 로드"""
        self.classifier = pipeline(
            "text-classification",
            model="facebook/bart-large-mnli",
            device=0 if self.device == "cuda" else -1
        )
    
    def predict(self, text: str) -> Dict[str, Any]:
        """편향성 분석 수행"""
        processed_text = self.preprocess_text(text)
        
        # 편향 유형별 분류
        bias_types = [
            "political bias",
            "gender bias", 
            "racial bias",
            "religious bias",
            "economic bias"
        ]
        
        bias_scores = {}
        for bias_type in bias_types:
            result = self.classifier(processed_text, candidate_labels=[bias_type, "neutral"])
            bias_scores[bias_type] = result['scores'][0]
        
        # 전체 편향 점수 계산
        total_bias_score = sum(bias_scores.values()) / len(bias_scores) * 100
        
        return {
            "bias_score": total_bias_score,
            "bias_breakdown": bias_scores,
            "text": text
        }
```

### **3단계: API 구현**

#### 3.1 분석 API (`app/api/v1/analysis.py`)
```python
# 구현 위치: src/python-server/app/api/v1/analysis.py
# 구현 함수: analyze_video(), get_analysis_result()

from fastapi import APIRouter, HTTPException, Depends
from app.models.analysis import AnalysisRequest, AnalysisResponse
from app.services.analysis import AnalysisService
from app.api.deps import get_analysis_service

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(
    request: AnalysisRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """비디오 분석 요청"""
    try:
        result = await analysis_service.analyze_video(
            video_id=request.video_id,
            video_url=request.video_url,
            transcript=request.transcript
        )
        return AnalysisResponse(
            success=True,
            data=result,
            message="분석이 완료되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{video_id}", response_model=AnalysisResponse)
async def get_analysis_result(
    video_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """분석 결과 조회"""
    try:
        result = await analysis_service.get_analysis_result(video_id)
        if not result:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
        
        return AnalysisResponse(
            success=True,
            data=result,
            message="분석 결과를 조회했습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 3.2 WebSocket API (`app/api/v1/websocket.py`)
```python
# 구현 위치: src/python-server/app/api/v1/websocket.py
# 구현 함수: websocket_endpoint()

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.analysis import AnalysisService
from app.api.deps import get_analysis_service
import json

router = APIRouter()

@router.websocket("/ws/analysis/{video_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    video_id: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """실시간 분석 WebSocket 엔드포인트"""
    await websocket.accept()
    
    try:
        # 분석 시작 알림
        await websocket.send_text(json.dumps({
            "type": "analysis_started",
            "video_id": video_id,
            "message": "분석을 시작합니다."
        }))
        
        # 실시간 분석 수행
        async for progress in analysis_service.analyze_video_realtime(video_id):
            await websocket.send_text(json.dumps({
                "type": "analysis_progress",
                "video_id": video_id,
                "progress": progress
            }))
        
        # 분석 완료 알림
        final_result = await analysis_service.get_analysis_result(video_id)
        await websocket.send_text(json.dumps({
            "type": "analysis_completed",
            "video_id": video_id,
            "result": final_result
        }))
        
    except WebSocketDisconnect:
        print(f"Client {video_id} disconnected")
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
```

### **4단계: 서비스 레이어 구현**

#### 4.1 분석 서비스 (`app/services/analysis.py`)
```python
# 구현 위치: src/python-server/app/services/analysis.py
# 구현 클래스: AnalysisService

from app.services.ai_models import AIModelService
from app.services.youtube import YouTubeService
from app.services.cache import CacheService
from app.models.analysis import AnalysisResult
from typing import AsyncGenerator, Dict, Any
import asyncio

class AnalysisService:
    def __init__(
        self,
        ai_service: AIModelService,
        youtube_service: YouTubeService,
        cache_service: CacheService
    ):
        self.ai_service = ai_service
        self.youtube_service = youtube_service
        self.cache_service = cache_service
    
    async def analyze_video(
        self,
        video_id: str,
        video_url: str = None,
        transcript: str = None
    ) -> AnalysisResult:
        """비디오 분석 수행"""
        # 캐시 확인
        cached_result = await self.cache_service.get_analysis(video_id)
        if cached_result:
            return cached_result
        
        # YouTube 데이터 수집
        if not transcript:
            video_data = await self.youtube_service.get_video_data(video_id)
            transcript = video_data.get('transcript', '')
        
        # AI 분석 수행
        sentiment_result = await self.ai_service.analyze_sentiment(transcript)
        bias_result = await self.ai_service.analyze_bias(transcript)
        credibility_result = await self.ai_service.analyze_credibility(transcript)
        
        # 종합 신뢰도 점수 계산
        overall_score = self._calculate_overall_score(
            sentiment_result, bias_result, credibility_result
        )
        
        # 결과 생성
        result = AnalysisResult(
            video_id=video_id,
            video_url=video_url,
            credibility_score=overall_score,
            sentiment_score=sentiment_result['sentiment_score'],
            bias_score=bias_result['bias_score'],
            analysis_breakdown={
                'sentiment': sentiment_result,
                'bias': bias_result,
                'credibility': credibility_result
            }
        )
        
        # 캐시 저장
        await self.cache_service.save_analysis(video_id, result)
        
        return result
    
    async def analyze_video_realtime(
        self, video_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """실시간 분석 진행상황"""
        yield {"step": "started", "progress": 0}
        
        # YouTube 데이터 수집
        yield {"step": "collecting_data", "progress": 20}
        video_data = await self.youtube_service.get_video_data(video_id)
        
        # 감정 분석
        yield {"step": "sentiment_analysis", "progress": 40}
        sentiment_result = await self.ai_service.analyze_sentiment(
            video_data.get('transcript', '')
        )
        
        # 편향 감지
        yield {"step": "bias_detection", "progress": 60}
        bias_result = await self.ai_service.analyze_bias(
            video_data.get('transcript', '')
        )
        
        # 신뢰도 분석
        yield {"step": "credibility_analysis", "progress": 80}
        credibility_result = await self.ai_service.analyze_credibility(
            video_data.get('transcript', '')
        )
        
        yield {"step": "completed", "progress": 100}
    
    def _calculate_overall_score(
        self,
        sentiment_result: Dict[str, Any],
        bias_result: Dict[str, Any],
        credibility_result: Dict[str, Any]
    ) -> float:
        """종합 신뢰도 점수 계산"""
        # 가중치 설정
        weights = {
            'sentiment': 0.2,
            'bias': 0.4,
            'credibility': 0.4
        }
        
        # 점수 계산
        sentiment_score = sentiment_result.get('sentiment_score', 50)
        bias_score = 100 - bias_result.get('bias_score', 50)  # 편향이 낮을수록 높은 점수
        credibility_score = credibility_result.get('credibility_score', 50)
        
        overall_score = (
            sentiment_score * weights['sentiment'] +
            bias_score * weights['bias'] +
            credibility_score * weights['credibility']
        )
        
        return round(overall_score, 2)
```

## 🧪 **테스트 구현 계획**

### 1. 단위 테스트
```python
# 구현 위치: src/python-server/tests/test_ai/test_sentiment.py
# 구현 함수: test_sentiment_analyzer()

import pytest
from app.ai.sentiment import SentimentAnalyzer

@pytest.mark.asyncio
async def test_sentiment_analyzer():
    """감정 분석 모델 테스트"""
    analyzer = SentimentAnalyzer("./models")
    
    # 긍정적 텍스트 테스트
    positive_result = await analyzer.predict("이 영상은 정말 좋습니다!")
    assert positive_result['sentiment_score'] > 60
    
    # 부정적 텍스트 테스트
    negative_result = await analyzer.predict("이 영상은 별로입니다.")
    assert negative_result['sentiment_score'] < 40
```

### 2. 통합 테스트
```python
# 구현 위치: src/python-server/tests/test_services/test_analysis_service.py
# 구현 함수: test_analysis_service()

import pytest
from app.services.analysis import AnalysisService
from app.services.ai_models import AIModelService
from app.services.youtube import YouTubeService
from app.services.cache import CacheService

@pytest.mark.asyncio
async def test_analysis_service():
    """분석 서비스 통합 테스트"""
    # 서비스 초기화
    ai_service = AIModelService()
    youtube_service = YouTubeService()
    cache_service = CacheService()
    
    analysis_service = AnalysisService(ai_service, youtube_service, cache_service)
    
    # 분석 수행
    result = await analysis_service.analyze_video(
        video_id="test123",
        transcript="이것은 테스트 텍스트입니다."
    )
    
    assert result.video_id == "test123"
    assert 0 <= result.credibility_score <= 100
    assert result.analysis_breakdown is not None
```

## 🚀 **성능 최적화 계획**

### 1. GPU 가속
```python
# 구현 위치: src/python-server/app/core/gpu_config.py
# 구현 함수: setup_gpu(), optimize_model()

import torch
from typing import Optional

def setup_gpu() -> Optional[str]:
    """GPU 설정 및 최적화"""
    if torch.cuda.is_available():
        device = "cuda"
        # GPU 메모리 최적화
        torch.cuda.empty_cache()
        torch.backends.cudnn.benchmark = True
        return device
    return "cpu"

def optimize_model(model, device: str):
    """모델 최적화"""
    if device == "cuda":
        model = model.cuda()
        model = torch.nn.DataParallel(model)
    return model
```

### 2. 배치 처리
```python
# 구현 위치: src/python-server/app/services/batch_processor.py
# 구현 클래스: BatchProcessor

class BatchProcessor:
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
    
    async def process_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """배치 단위로 텍스트 처리"""
        results = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = await self._process_single_batch(batch)
            results.extend(batch_results)
        
        return results
```

## 📊 **모니터링 및 로깅**

### 1. 로깅 시스템
```python
# 구현 위치: src/python-server/app/core/logging.py
# 구현 함수: setup_logging()

import logging
from app.core.config import settings

def setup_logging():
    """로깅 시스템 설정"""
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
```

### 2. 성능 메트릭
```python
# 구현 위치: src/python-server/app/core/metrics.py
# 구현 함수: track_performance()

import time
from functools import wraps

def track_performance(func):
    """성능 추적 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        # 성능 메트릭 기록
        processing_time = (end_time - start_time) * 1000  # ms
        print(f"{func.__name__} 실행 시간: {processing_time:.2f}ms")
        
        return result
    return wrapper
```

## 🎯 **구현 완료 체크리스트**

- [ ] 기본 서버 구조 및 설정
- [ ] AI 모델 클래스 구현
- [ ] 감정 분석 모델
- [ ] 편향 감지 모델
- [ ] 신뢰도 분석 모델
- [ ] 분석 API 엔드포인트
- [ ] WebSocket 실시간 통신
- [ ] 분석 서비스 로직
- [ ] YouTube API 연동

- [ ] 팩트 체커 모델 테스트
- [ ] 콘텐츠 분류 모델 테스트
- [ ] 성능 최적화
- [ ] 모니터링 시스템
- [ ] 배치 처리 최적화