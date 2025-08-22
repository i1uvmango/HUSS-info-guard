# API 통합 구현 계획

## 🎯 **API 통합 개요**
Info-Guard의 API 통합은 Python AI 서버, Node.js 백엔드 서버, Chrome Extension 간의 원활한 데이터 흐름을 담당합니다. RESTful API, WebSocket, 그리고 실시간 통신을 통해 전체 시스템을 연결합니다.

## 🏗️ **API 통합 아키텍처**

### 1. 전체 통합 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Chrome Extension│    │  Node.js Server │    │  Python Server  │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (AI Analysis) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YouTube API   │    │   PostgreSQL    │    │   AI Models     │
│   (Data Source) │    │   (Database)    │    │   (Analysis)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. API 엔드포인트 구조
```
/api/v1/
├── health/              # 헬스체크
├── analysis/            # 분석 관련 API
├── feedback/            # 피드백 API
├── user/                # 사용자 관리
├── channel/             # 채널 정보
└── websocket/           # 실시간 통신
```

## 🔌 **핵심 API 통합**

### 1. 분석 API 통합
```python
# 구현 위치: src/python-server/app/api/v1/analysis.py
# 구현 클래스: AnalysisRouter

from fastapi import APIRouter, HTTPException, Depends
from app.services.analysis import AnalysisService
from app.models.analysis import AnalysisRequest, AnalysisResponse
from app.core.deps import get_current_user

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(
    request: AnalysisRequest,
    current_user = Depends(get_current_user)
):
    """비디오 신뢰도 분석"""
    try:
        analysis_service = AnalysisService()
        result = await analysis_service.analyze_video(
            video_id=request.video_id,
            title=request.title,
            description=request.description,
            user_id=current_user.id
        )
        
        return AnalysisResponse(
            analysis_id=result.id,
            video_id=result.video_id,
            overall_score=result.overall_score,
            credibility_score=result.credibility_score,
            bias_score=result.bias_score,
            sentiment_score=result.sentiment_score,
            fact_check_score=result.fact_check_score,
            processing_time=result.processing_time,
            status=result.status
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    """분석 결과 조회"""
    try:
        analysis_service = AnalysisService()
        result = await analysis_service.get_analysis(analysis_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. WebSocket 실시간 통신
```python
# 구현 위치: src/python-server/app/api/v1/websocket.py
# 구현 클래스: WebSocketManager

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.analysis_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """WebSocket 연결"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # 연결 확인 메시지
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "client_id": client_id,
            "message": "WebSocket 연결이 성공했습니다."
        }))
    
    async def disconnect(self, client_id: str):
        """WebSocket 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.analysis_tasks:
            self.analysis_tasks[client_id].cancel()
            del self.analysis_tasks[client_id]
    
    async def send_analysis_progress(self, client_id: str, progress: Dict):
        """분석 진행률 전송"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps({
                "type": "analysis_progress",
                "data": progress
            }))
    
    async def send_analysis_result(self, client_id: str, result: Dict):
        """분석 결과 전송"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps({
                "type": "analysis_complete",
                "data": result
            }))

manager = WebSocketManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 엔드포인트"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입에 따른 처리
            if message["type"] == "start_analysis":
                await handle_analysis_request(client_id, message["data"])
            elif message["type"] == "cancel_analysis":
                await handle_cancel_analysis(client_id)
            
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket 오류: {e}")
        await manager.disconnect(client_id)

async def handle_analysis_request(client_id: str, data: Dict):
    """분석 요청 처리"""
    try:
        # 분석 작업 시작
        analysis_service = AnalysisService()
        analysis_task = asyncio.create_task(
            analysis_service.analyze_with_progress(
                video_id=data["video_id"],
                title=data["title"],
                description=data["description"],
                client_id=client_id,
                manager=manager
            )
        )
        
        manager.analysis_tasks[client_id] = analysis_task
        await analysis_task
        
    except Exception as e:
        await manager.send_analysis_progress(client_id, {
            "status": "error",
            "message": str(e)
        })
```

### 3. Node.js 서버 API 통합
```javascript
// 구현 위치: src/nodejs-server/src/api/routes/analysis.js
// 구현 클래스: AnalysisRouter

const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const axios = require('axios');

const prisma = new PrismaClient();
const PYTHON_SERVER_URL = process.env.PYTHON_SERVER_URL || 'http://localhost:8000';

// 비디오 분석 요청
router.post('/analyze', async (req, res) => {
    try {
        const { video_id, title, description, user_id } = req.body;
        
        // 1. 기존 분석 결과 확인
        const existingAnalysis = await prisma.analysis.findFirst({
            where: { video_id },
            include: { video: true, user: true }
        });
        
        if (existingAnalysis) {
            return res.json({
                success: true,
                data: existingAnalysis,
                message: '기존 분석 결과를 반환합니다.'
            });
        }
        
        // 2. Python AI 서버에 분석 요청
        const analysisResponse = await axios.post(`${PYTHON_SERVER_URL}/api/v1/analyze`, {
            video_id,
            title,
            description,
            user_id
        });
        
        // 3. 분석 결과를 데이터베이스에 저장
        const analysisData = analysisResponse.data;
        const savedAnalysis = await prisma.analysis.create({
            data: {
                video_id: analysisData.video_id,
                user_id: analysisData.user_id,
                credibility_score: analysisData.credibility_score,
                bias_score: analysisData.bias_score,
                sentiment_score: analysisData.sentiment_score,
                fact_check_score: analysisData.fact_check_score,
                overall_score: analysisData.overall_score,
                analysis_data: analysisData.detailed_analysis,
                processing_time: analysisData.processing_time,
                status: 'completed'
            },
            include: {
                video: true,
                user: true
            }
        });
        
        res.json({
            success: true,
            data: savedAnalysis,
            message: '분석이 완료되었습니다.'
        });
        
    } catch (error) {
        console.error('분석 요청 오류:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 분석 결과 조회
router.get('/:analysis_id', async (req, res) => {
    try {
        const { analysis_id } = req.params;
        
        const analysis = await prisma.analysis.findUnique({
            where: { id: analysis_id },
            include: {
                video: {
                    include: { channel: true }
                },
                user: true,
                feedbacks: {
                    include: { user: true }
                }
            }
        });
        
        if (!analysis) {
            return res.status(404).json({
                success: false,
                error: '분석 결과를 찾을 수 없습니다.'
            });
        }
        
        res.json({
            success: true,
            data: analysis
        });
        
    } catch (error) {
        console.error('분석 결과 조회 오류:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

module.exports = router;
```

## 🔄 **실시간 데이터 동기화**

### 1. Socket.IO 통합
```javascript
// 구현 위치: src/nodejs-server/src/services/socket.js
// 구현 클래스: SocketService

const { Server } = require('socket.io');

class SocketService {
    constructor(server) {
        this.io = new Server(server, {
            cors: {
                origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
                methods: ["GET", "POST"]
            }
        });
        
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.io.on('connection', (socket) => {
            console.log('클라이언트 연결:', socket.id);
            
            // 분석 진행률 구독
            socket.on('subscribe_analysis', (analysisId) => {
                socket.join(`analysis_${analysisId}`);
                console.log(`클라이언트 ${socket.id}가 분석 ${analysisId}를 구독했습니다.`);
            });
            
            // 분석 진행률 구독 해제
            socket.on('unsubscribe_analysis', (analysisId) => {
                socket.leave(`analysis_${analysisId}`);
                console.log(`클라이언트 ${socket.id}가 분석 ${analysisId} 구독을 해제했습니다.`);
            });
            
            // 연결 해제
            socket.on('disconnect', () => {
                console.log('클라이언트 연결 해제:', socket.id);
            });
        });
    }
    
    // 분석 진행률 브로드캐스트
    broadcastAnalysisProgress(analysisId, progress) {
        this.io.to(`analysis_${analysisId}`).emit('analysis_progress', {
            analysis_id: analysisId,
            progress: progress
        });
    }
    
    // 분석 완료 알림
    broadcastAnalysisComplete(analysisId, result) {
        this.io.to(`analysis_${analysisId}`).emit('analysis_complete', {
            analysis_id: analysisId,
            result: result
        });
    }
    
    // 에러 알림
    broadcastError(analysisId, error) {
        this.io.to(`analysis_${analysisId}`).emit('analysis_error', {
            analysis_id: analysisId,
            error: error.message
        });
    }
}

module.exports = SocketService;
```

### 2. 데이터 동기화 스케줄러
```javascript
// 구현 위치: src/nodejs-server/src/services/syncScheduler.js
// 구현 클래스: SyncScheduler

const cron = require('node-cron');
const axios = require('axios');

class SyncScheduler {
    constructor() {
        this.pythonServerUrl = process.env.PYTHON_SERVER_URL || 'http://localhost:8000';
        this.syncInterval = process.env.SYNC_INTERVAL || '*/5 * * * *'; // 5분마다
        
        this.startSync();
    }
    
    startSync() {
        // 정기적인 데이터 동기화
        cron.schedule(this.syncInterval, async () => {
            try {
                await this.syncAnalysisData();
                await this.syncUserData();
                await this.syncChannelData();
                
                console.log('데이터 동기화 완료:', new Date().toISOString());
                
            } catch (error) {
                console.error('데이터 동기화 오류:', error);
            }
        });
        
        // 매일 자정에 전체 동기화
        cron.schedule('0 0 * * *', async () => {
            try {
                await this.fullSync();
                console.log('전체 데이터 동기화 완료:', new Date().toISOString());
                
            } catch (error) {
                console.error('전체 데이터 동기화 오류:', error);
            }
        });
    }
    
    async syncAnalysisData() {
        try {
            // Python 서버에서 최신 분석 데이터 가져오기
            const response = await axios.get(`${this.pythonServerUrl}/api/v1/analyses/recent`);
            const recentAnalyses = response.data;
            
            // 데이터베이스 업데이트
            for (const analysis of recentAnalyses) {
                await this.updateAnalysisInDatabase(analysis);
            }
            
        } catch (error) {
            console.error('분석 데이터 동기화 오류:', error);
        }
    }
    
    async updateAnalysisInDatabase(analysisData) {
        try {
            await prisma.analysis.upsert({
                where: { id: analysisData.id },
                update: {
                    credibility_score: analysisData.credibility_score,
                    bias_score: analysisData.bias_score,
                    sentiment_score: analysisData.sentiment_score,
                    fact_check_score: analysisData.fact_check_score,
                    overall_score: analysisData.overall_score,
                    analysis_data: analysisData.detailed_analysis,
                    updated_at: new Date()
                },
                create: {
                    id: analysisData.id,
                    video_id: analysisData.video_id,
                    user_id: analysisData.user_id,
                    credibility_score: analysisData.credibility_score,
                    bias_score: analysisData.bias_score,
                    sentiment_score: analysisData.sentiment_score,
                    fact_check_score: analysisData.fact_check_score,
                    overall_score: analysisData.overall_score,
                    analysis_data: analysisData.detailed_analysis,
                    status: 'completed'
                }
            });
            
        } catch (error) {
            console.error('분석 데이터 업데이트 오류:', error);
        }
    }
}

module.exports = SyncScheduler;
```

## 🔒 **보안 및 인증**

### 1. JWT 인증 미들웨어
```javascript
// 구현 위치: src/nodejs-server/src/middleware/auth.js
// 구현 함수: authenticateToken

const jwt = require('jsonwebtoken');

const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN
    
    if (!token) {
        return res.status(401).json({
            success: false,
            error: '인증 토큰이 필요합니다.'
        });
    }
    
    jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({
                success: false,
                error: '유효하지 않은 토큰입니다.'
            });
        }
        
        req.user = user;
        next();
    });
};

module.exports = { authenticateToken };
```

### 2. Rate Limiting
```javascript
// 구현 위치: src/nodejs-server/src/middleware/rateLimit.js
// 구현 함수: createRateLimiter

const rateLimit = require('express-rate-limit');

const createRateLimiter = (windowMs, max, message) => {
    return rateLimit({
        windowMs: windowMs,
        max: max,
        message: {
            success: false,
            error: message || '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.'
        },
        standardHeaders: true,
        legacyHeaders: false
    });
};

// API별 Rate Limiting
const analysisLimiter = createRateLimiter(
    15 * 60 * 1000, // 15분
    10, // 최대 10회
    '분석 요청이 너무 많습니다. 15분 후 다시 시도해주세요.'
);

const authLimiter = createRateLimiter(
    15 * 60 * 1000, // 15분
    5, // 최대 5회
    '인증 시도가 너무 많습니다. 15분 후 다시 시도해주세요.'
);

module.exports = { analysisLimiter, authLimiter };
```

## 📊 **API 모니터링 및 로깅**

### 1. API 요청 로깅
```javascript
// 구현 위치: src/nodejs-server/src/middleware/logger.js
// 구현 함수: apiLogger

const winston = require('winston');

const apiLogger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: 'api.log' }),
        new winston.transports.Console()
    ]
});

const logApiRequest = (req, res, next) => {
    const startTime = Date.now();
    
    // 응답 완료 후 로깅
    res.on('finish', () => {
        const duration = Date.now() - startTime;
        
        apiLogger.info({
            method: req.method,
            url: req.url,
            status: res.statusCode,
            duration: `${duration}ms`,
            user_agent: req.get('User-Agent'),
            ip: req.ip,
            timestamp: new Date().toISOString()
        });
    });
    
    next();
};

module.exports = { logApiRequest, apiLogger };
```

### 2. API 성능 메트릭
```javascript
// 구현 위치: src/nodejs-server/src/middleware/metrics.js
// 구현 함수: collectMetrics

const collectMetrics = (req, res, next) => {
    const startTime = process.hrtime();
    
    res.on('finish', () => {
        const [seconds, nanoseconds] = process.hrtime(startTime);
        const duration = seconds * 1000 + nanoseconds / 1000000; // 밀리초
        
        // 메트릭 수집
        global.apiMetrics = global.apiMetrics || {
            totalRequests: 0,
            totalDuration: 0,
            averageDuration: 0,
            requestCounts: {},
            errorCounts: {}
        };
        
        global.apiMetrics.totalRequests++;
        global.apiMetrics.totalDuration += duration;
        global.apiMetrics.averageDuration = global.apiMetrics.totalDuration / global.apiMetrics.totalRequests;
        
        // 엔드포인트별 요청 수
        const endpoint = `${req.method} ${req.route?.path || req.path}`;
        global.apiMetrics.requestCounts[endpoint] = (global.apiMetrics.requestCounts[endpoint] || 0) + 1;
        
        // 에러 수
        if (res.statusCode >= 400) {
            global.apiMetrics.errorCounts[endpoint] = (global.apiMetrics.errorCounts[endpoint] || 0) + 1;
        }
    });
    
    next();
};

module.exports = { collectMetrics };
```

## 🎯 **구현 완료 체크리스트**

- [ ] Python AI 서버 API
- [ ] Node.js 백엔드 API
- [ ] WebSocket 실시간 통신
- [ ] 기본 인증 시스템
- [ ] API 요청 로깅
- [ ] 기본 에러 처리

- [ ] 고급 인증 시스템
- [ ] Rate Limiting 완성
- [ ] API 성능 모니터링

- [ ] API 버전 관리
- [ ] API 문서 자동 생성
- [ ] 고급 보안 기능
- [ ] API 테스트 자동화