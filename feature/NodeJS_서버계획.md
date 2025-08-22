# Node.js 서버 구현 계획

## 🎯 **Node.js 서버 개요**
Info-Guard Node.js 서버는 사용자 관리, 데이터베이스 연동, 그리고 Python AI 서버와의 중계 역할을 담당합니다. Express.js 기반으로 구축되어 RESTful API와 WebSocket 통신을 지원합니다.

## 🏗️ **아키텍처 구조**

### 1. 디렉토리 구조
```
src/nodejs-server/
├── server.js                    # 메인 서버 진입점
├── package.json                 # 의존성 패키지
├── prisma/                      # 데이터베이스 스키마
│   └── schema.prisma
├── src/                         # 소스 코드
│   ├── index.js                 # 애플리케이션 진입점
│   ├── api/                     # API 라우터
│   │   ├── routes/              # 라우트 정의
│   │   │   ├── analysis.js      # 분석 관련 API
│   │   │   ├── feedback.js      # 피드백 API
│   │   │   ├── health.js        # 헬스체크
│   │   │   └── user.js          # 사용자 관리
│   ├── middleware/              # 미들웨어
│   │   ├── errorHandler.js      # 에러 처리
│   │   ├── notFoundHandler.js   # 404 처리
│   │   └── auth.js              # 인증 미들웨어
│   ├── services/                # 비즈니스 로직
│   │   ├── database.js          # 데이터베이스 연결
│   │   ├── redis.js             # Redis 연결
│   │   └── socket.js            # WebSocket 서비스
│   └── utils/                   # 유틸리티
│       └── logger.js            # 로깅 시스템
├── database/                    # 데이터베이스 관련
│   ├── connection.js            # 연결 관리
│   ├── init.js                  # 초기화
│   ├── repositories/            # 데이터 접근 계층
│   │   ├── analysisRepository.js
│   │   ├── channelRepository.js
│   │   └── feedbackRepository.js
│   └── seeds/                   # 시드 데이터
│       └── seedData.js
└── tests/                       # 테스트 코드
```

## 🚀 **구현 단계별 계획**

### **1단계: 기본 서버 구조**

#### 1.1 메인 서버 파일 (`server.js`)
```javascript
// 구현 위치: src/nodejs-server/server.js
// 구현 함수: startServer()

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const { Server } = require('socket.io');

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
    methods: ["GET", "POST"]
  }
});

// 보안 미들웨어
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// 속도 제한
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15분
  max: 100 // IP당 최대 요청 수
});
app.use(limiter);

// 라우터 등록
app.use('/api/health', require('./routes/health'));
app.use('/api/analysis', require('./routes/analysis'));
app.use('/api/feedback', require('./routes/feedback'));
app.use('/api/user', require('./routes/user'));

// WebSocket 연결 처리
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Node.js server running on port ${PORT}`);
});

module.exports = { app, server, io };
```

#### 1.2 데이터베이스 스키마 (`prisma/schema.prisma`)
```prisma
// 구현 위치: src/nodejs-server/prisma/schema.prisma
// 구현 모델: User, Analysis, Feedback, Channel

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  
  analyses   Analysis[]
  feedbacks  Feedback[]
  
  @@map("users")
}

model Analysis {
  id              String   @id @default(cuid())
  videoId         String   @unique
  videoUrl        String?
  videoTitle      String?
  channelId       String?
  credibilityScore Float
  sentimentScore   Float
  biasScore        Float
  analysisData     Json
  status          String   @default("pending") // pending, processing, completed, failed
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  user      User        @relation(fields: [userId], references: [id])
  userId    String
  channel   Channel?    @relation(fields: [channelId], references: [id])
  feedbacks Feedback[]
  
  @@map("analyses")
}

model Feedback {
  id          String   @id @default(cuid())
  analysisId  String
  userId      String
  rating      Int      // 1-5 점수
  comment     String?
  createdAt   DateTime @default(now())
  
  analysis Analysis @relation(fields: [analysisId], references: [id])
  user     User     @relation(fields: [userId], references: [id])
  
  @@map("feedbacks")
}

model Channel {
  id          String   @id @default(cuid())
  channelId   String   @unique
  channelName String
  subscriberCount Int?
  videoCount  Int?
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  analyses Analysis[]
  
  @@map("channels")
}
```

### **2단계: API 라우터 구현**

#### 2.1 분석 API (`src/api/routes/analysis.js`)
```javascript
// 구현 위치: src/nodejs-server/src/api/routes/analysis.js
// 구현 함수: createAnalysis(), getAnalysis(), updateAnalysis()

const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// 분석 생성
router.post('/', async (req, res) => {
  try {
    const { videoId, videoUrl, videoTitle, channelId, userId } = req.body;
    
    // 기존 분석 확인
    const existingAnalysis = await prisma.analysis.findUnique({
      where: { videoId }
    });
    
    if (existingAnalysis) {
      return res.json({
        success: true,
        data: existingAnalysis,
        message: '이미 분석된 비디오입니다.'
      });
    }
    
    // 새 분석 생성
    const analysis = await prisma.analysis.create({
      data: {
        videoId,
        videoUrl,
        videoTitle,
        channelId,
        userId,
        credibilityScore: 0,
        sentimentScore: 0,
        biasScore: 0,
        analysisData: {},
        status: 'pending'
      }
    });
    
    res.json({
      success: true,
      data: analysis,
      message: '분석이 요청되었습니다.'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// 분석 결과 조회
router.get('/:videoId', async (req, res) => {
  try {
    const { videoId } = req.params;
    
    const analysis = await prisma.analysis.findUnique({
      where: { videoId },
      include: {
        user: { select: { name: true, email: true } },
        channel: { select: { channelName: true } },
        feedbacks: {
          include: { user: { select: { name: true } } }
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
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// 분석 상태 업데이트
router.patch('/:videoId', async (req, res) => {
  try {
    const { videoId } = req.params;
    const { status, credibilityScore, sentimentScore, biasScore, analysisData } = req.body;
    
    const updatedAnalysis = await prisma.analysis.update({
      where: { videoId },
      data: {
        status,
        credibilityScore,
        sentimentScore,
        biasScore,
        analysisData,
        updatedAt: new Date()
      }
    });
    
    res.json({
      success: true,
      data: updatedAnalysis,
      message: '분석이 업데이트되었습니다.'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;
```

#### 2.2 피드백 API (`src/api/routes/feedback.js`)
```javascript
// 구현 위치: src/nodejs-server/src/api/routes/feedback.js
// 구현 함수: createFeedback(), getFeedbacks(), updateFeedback()

const express = require('express');
const router = express.Router();
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// 피드백 생성
router.post('/', async (req, res) => {
  try {
    const { analysisId, userId, rating, comment } = req.body;
    
    // 기존 피드백 확인
    const existingFeedback = await prisma.feedback.findFirst({
      where: {
        analysisId,
        userId
      }
    });
    
    if (existingFeedback) {
      return res.status(400).json({
        success: false,
        error: '이미 피드백을 작성했습니다.'
      });
    }
    
    // 새 피드백 생성
    const feedback = await prisma.feedback.create({
      data: {
        analysisId,
        userId,
        rating,
        comment
      },
      include: {
        user: { select: { name: true } }
      }
    });
    
    res.json({
      success: true,
      data: feedback,
      message: '피드백이 등록되었습니다.'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// 분석별 피드백 조회
router.get('/analysis/:analysisId', async (req, res) => {
  try {
    const { analysisId } = req.params;
    
    const feedbacks = await prisma.feedback.findMany({
      where: { analysisId },
      include: {
        user: { select: { name: true } }
      },
      orderBy: { createdAt: 'desc' }
    });
    
    res.json({
      success: true,
      data: feedbacks
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;
```

### **3단계: 서비스 레이어 구현**

#### 3.1 데이터베이스 서비스 (`src/services/database.js`)
```javascript
// 구현 위치: src/nodejs-server/src/services/database.js
// 구현 클래스: DatabaseService

const { PrismaClient } = require('@prisma/client');

class DatabaseService {
  constructor() {
    this.prisma = new PrismaClient();
  }
  
  async connect() {
    try {
      await this.prisma.$connect();
      console.log('Database connected successfully');
    } catch (error) {
      console.error('Database connection failed:', error);
      throw error;
    }
  }
  
  async disconnect() {
    await this.prisma.$disconnect();
  }
  
  async healthCheck() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return true;
    } catch (error) {
      return false;
    }
  }
  
  getPrisma() {
    return this.prisma;
  }
}

module.exports = DatabaseService;
```

#### 3.2 Redis 서비스 (`src/services/redis.js`)
```javascript
// 구현 위치: src/nodejs-server/src/services/redis.js
// 구현 클래스: RedisService

const Redis = require('ioredis');

class RedisService {
  constructor() {
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
    
    this.redis.on('error', (error) => {
      console.error('Redis connection error:', error);
    });
    
    this.redis.on('connect', () => {
      console.log('Redis connected successfully');
    });
  }
  
  async set(key, value, expireSeconds = 3600) {
    try {
      await this.redis.set(key, JSON.stringify(value), 'EX', expireSeconds);
      return true;
    } catch (error) {
      console.error('Redis set error:', error);
      return false;
    }
  }
  
  async get(key) {
    try {
      const value = await this.redis.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error('Redis get error:', error);
      return null;
    }
  }
  
  async delete(key) {
    try {
      await this.redis.del(key);
      return true;
    } catch (error) {
      console.error('Redis delete error:', error);
      return false;
    }
  }
  
  async healthCheck() {
    try {
      await this.redis.ping();
      return true;
    } catch (error) {
      return false;
    }
  }
}

module.exports = RedisService;
```

### **4단계: 미들웨어 구현**

#### 4.1 에러 핸들러 (`src/middleware/errorHandler.js`)
```javascript
// 구현 위치: src/nodejs-server/src/middleware/errorHandler.js
// 구현 함수: errorHandler()

const errorHandler = (err, req, res, next) => {
  console.error('Error:', err);
  
  // Prisma 에러 처리
  if (err.code === 'P2002') {
    return res.status(400).json({
      success: false,
      error: '중복된 데이터입니다.'
    });
  }
  
  if (err.code === 'P2025') {
    return res.status(404).json({
      success: false,
      error: '데이터를 찾을 수 없습니다.'
    });
  }
  
  // 기본 에러 응답
  const statusCode = err.statusCode || 500;
  const message = err.message || '서버 내부 오류가 발생했습니다.';
  
  res.status(statusCode).json({
    success: false,
    error: message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
};

module.exports = errorHandler;
```

#### 4.2 인증 미들웨어 (`src/middleware/auth.js`)
```javascript
// 구현 위치: src/nodejs-server/src/middleware/auth.js
// 구현 함수: authenticateUser()

const jwt = require('jsonwebtoken');
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const authenticateUser = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({
        success: false,
        error: '인증 토큰이 필요합니다.'
      });
    }
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await prisma.user.findUnique({
      where: { id: decoded.userId }
    });
    
    if (!user) {
      return res.status(401).json({
        success: false,
        error: '유효하지 않은 사용자입니다.'
      });
    }
    
    req.user = user;
    next();
  } catch (error) {
    if (error.name === 'JsonWebTokenError') {
      return res.status(401).json({
        success: false,
        error: '유효하지 않은 토큰입니다.'
      });
    }
    
    res.status(500).json({
      success: false,
      error: '인증 처리 중 오류가 발생했습니다.'
    });
  }
};

module.exports = { authenticateUser };
```

## 🧪 **테스트 구현 계획**

### 1. 단위 테스트
```javascript
// 구현 위치: src/nodejs-server/tests/test_api/test_analysis.js
// 구현 함수: testCreateAnalysis()

const request = require('supertest');
const { app } = require('../../server');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

describe('Analysis API', () => {
  beforeAll(async () => {
    await prisma.analysis.deleteMany();
  });
  
  afterAll(async () => {
    await prisma.$disconnect();
  });
  
  test('POST /api/analysis - 분석 생성', async () => {
    const response = await request(app)
      .post('/api/analysis')
      .send({
        videoId: 'test123',
        videoUrl: 'https://youtube.com/watch?v=test123',
        userId: 'user123'
      });
    
    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.data.videoId).toBe('test123');
  });
});
```

## 🚀 **성능 최적화 계획**

### 1. 캐싱 전략
```javascript
// 구현 위치: src/nodejs-server/src/services/cache.js
// 구현 클래스: CacheService

class CacheService {
  constructor(redisService) {
    this.redis = redisService;
    this.defaultTTL = 3600; // 1시간
  }
  
  async getAnalysis(videoId) {
    const cacheKey = `analysis:${videoId}`;
    return await this.redis.get(cacheKey);
  }
  
  async setAnalysis(videoId, data, ttl = this.defaultTTL) {
    const cacheKey = `analysis:${videoId}`;
    return await this.redis.set(cacheKey, data, ttl);
  }
  
  async invalidateAnalysis(videoId) {
    const cacheKey = `analysis:${videoId}`;
    return await this.redis.delete(cacheKey);
  }
}
```

### 2. 데이터베이스 최적화
```javascript
// 구현 위치: src/nodejs-server/database/repositories/analysisRepository.js
// 구현 클래스: AnalysisRepository

class AnalysisRepository {
  constructor(prisma) {
    this.prisma = prisma;
  }
  
  async findAnalysisWithDetails(videoId) {
    return await this.prisma.analysis.findUnique({
      where: { videoId },
      include: {
        user: { select: { name: true, email: true } },
        channel: { select: { channelName: true } },
        feedbacks: {
          include: { user: { select: { name: true } } }
        }
      }
    });
  }
  
  async findAnalysesByUser(userId, page = 1, limit = 10) {
    const skip = (page - 1) * limit;
    
    const [analyses, total] = await Promise.all([
      this.prisma.analysis.findMany({
        where: { userId },
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' }
      }),
      this.prisma.analysis.count({ where: { userId } })
    ]);
    
    return { analyses, total, page, limit };
  }
}
```

## 📊 **모니터링 및 로깅**

### 1. 로깅 시스템
```javascript
// 구현 위치: src/nodejs-server/src/utils/logger.js
// 구현 함수: setupLogger()

const winston = require('winston');

const setupLogger = () => {
  return winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.errors({ stack: true }),
      winston.format.json()
    ),
    transports: [
      new winston.transports.File({ filename: 'error.log', level: 'error' }),
      new winston.transports.File({ filename: 'combined.log' }),
      new winston.transports.Console({
        format: winston.format.simple()
      })
    ]
  });
};

module.exports = { setupLogger };
```

## 🎯 **구현 완료 체크리스트**

- [ ] 기본 서버 구조 및 설정
- [ ] 데이터베이스 스키마 정의
- [ ] 분석 API 엔드포인트
- [ ] 피드백 API 엔드포인트
- [ ] 데이터베이스 서비스
- [ ] Redis 캐시 서비스
- [ ] 에러 처리 미들웨어
- [ ] 인증 미들웨어

- [ ] 사용자 관리 API
- [ ] 채널 관리 API
- [ ] WebSocket 실시간 통신
- [ ] 성능 모니터링
- [ ] 보안 강화