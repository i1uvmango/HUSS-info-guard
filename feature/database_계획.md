# 데이터베이스 구현 계획

## 🎯 **데이터베이스 개요**
Info-Guard 프로젝트의 데이터베이스는 PostgreSQL을 메인 데이터베이스로, Redis를 캐싱 및 세션 관리용으로 사용합니다. YouTube 영상 분석 결과, 사용자 정보, 피드백 데이터를 체계적으로 관리합니다.

## 🏗️ **데이터베이스 아키텍처**

### 1. 전체 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │      Redis      │    │   Backup/Archive│
│   (Main DB)     │◄──►│   (Cache/Queue) │◄──►│   (Data Store)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prisma ORM    │    │   Connection    │    │   Monitoring    │
│   (Schema)      │    │   Pool          │    │   (Health)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. 디렉토리 구조
```
src/
├── database/
│   ├── connection.js           # 데이터베이스 연결 관리
│   ├── init.js                 # 초기화 및 마이그레이션
│   ├── prisma/                 # Prisma 스키마
│   │   └── schema.prisma
│   ├── repositories/           # 데이터 접근 계층
│   │   ├── analysisRepository.js
│   │   ├── channelRepository.js
│   │   ├── feedbackRepository.js
│   │   └── userRepository.js
│   ├── seeds/                  # 시드 데이터
│   │   └── seedData.js
│   └── monitoring/             # 모니터링 및 백업
│       ├── dbMonitor.js
│       └── backup.sh
```

## 🗄️ **PostgreSQL 스키마 설계**

### 1. 핵심 테이블 구조

#### **users 테이블**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

#### **channels 테이블**
```sql
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id VARCHAR(50) UNIQUE NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    subscriber_count INTEGER DEFAULT 0,
    view_count BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT false
);
```

#### **videos 테이블**
```sql
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(50) UNIQUE NOT NULL,
    channel_id UUID REFERENCES channels(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    duration INTEGER, -- 초 단위
    view_count BIGINT DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    dislike_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **analyses 테이블**
```sql
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id),
    user_id UUID REFERENCES users(id),
    credibility_score DECIMAL(5,2), -- 0.00 ~ 100.00
    bias_score DECIMAL(5,2),        -- -100.00 ~ 100.00
    sentiment_score DECIMAL(5,2),   -- -100.00 ~ 100.00
    fact_check_score DECIMAL(5,2),  -- 0.00 ~ 100.00
    overall_score DECIMAL(5,2),     -- 0.00 ~ 100.00
    analysis_data JSONB,            -- 상세 분석 결과
    processing_time INTEGER,        -- 밀리초 단위
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **feedbacks 테이블**
```sql
CREATE TABLE feedbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID REFERENCES analyses(id),
    user_id UUID REFERENCES users(id),
    feedback_type VARCHAR(20) NOT NULL, -- 'accurate', 'inaccurate', 'helpful'
    comment TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 인덱스 설계
```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_videos_channel_id ON videos(channel_id);
CREATE INDEX idx_videos_published_at ON videos(published_at);
CREATE INDEX idx_analyses_video_id ON analyses(video_id);
CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_created_at ON analyses(created_at);
CREATE INDEX idx_feedbacks_analysis_id ON feedbacks(analysis_id);
CREATE INDEX idx_feedbacks_user_id ON feedbacks(user_id);

-- 복합 인덱스
CREATE INDEX idx_analyses_video_user ON analyses(video_id, user_id);
CREATE INDEX idx_videos_channel_published ON videos(channel_id, published_at);
```

## 🔄 **Redis 캐싱 전략**

### 1. 캐시 구조
```javascript
// 구현 위치: src/database/redis.js
// 구현 클래스: RedisService

class RedisService {
    constructor() {
        this.redis = new Redis({
            host: process.env.REDIS_HOST || 'localhost',
            port: process.env.REDIS_PORT || 6379,
            password: process.env.REDIS_PASSWORD,
            db: process.env.REDIS_DB || 0
        });
    }

    // 분석 결과 캐싱 (TTL: 1시간)
    async cacheAnalysisResult(videoId, analysisData) {
        const key = `analysis:${videoId}`;
        await this.redis.setex(key, 3600, JSON.stringify(analysisData));
    }

    // 사용자 세션 관리 (TTL: 24시간)
    async setUserSession(sessionId, userData) {
        const key = `session:${sessionId}`;
        await this.redis.setex(key, 86400, JSON.stringify(userData));
    }

    // 요청 제한 (Rate Limiting)
    async incrementRequestCount(ip, endpoint) {
        const key = `rate_limit:${ip}:${endpoint}`;
        const count = await this.redis.incr(key);
        if (count === 1) {
            await this.redis.expire(key, 60); // 1분
        }
        return count;
    }
}
```

### 2. 캐시 키 전략
```
analysis:{videoId}           # 비디오 분석 결과 (1시간)
session:{sessionId}          # 사용자 세션 (24시간)
rate_limit:{ip}:{endpoint}  # 요청 제한 (1분)
user:{userId}               # 사용자 정보 (30분)
channel:{channelId}         # 채널 정보 (1시간)
```

## 🗃️ **데이터 접근 계층 (Repository Pattern)**

### 1. 분석 데이터 Repository
```javascript
// 구현 위치: src/database/repositories/analysisRepository.js
// 구현 클래스: AnalysisRepository

class AnalysisRepository {
    constructor(prisma) {
        this.prisma = prisma;
    }

    async createAnalysis(analysisData) {
        return await this.prisma.analysis.create({
            data: analysisData,
            include: {
                video: {
                    include: {
                        channel: true
                    }
                },
                user: {
                    select: {
                        id: true,
                        name: true,
                        email: true
                    }
                }
            }
        });
    }

    async findAnalysisByVideoId(videoId) {
        return await this.prisma.analysis.findFirst({
            where: { videoId },
            include: {
                video: true,
                user: true,
                feedbacks: {
                    include: {
                        user: {
                            select: {
                                name: true
                            }
                        }
                    }
                }
            },
            orderBy: {
                createdAt: 'desc'
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
                include: {
                    video: true
                },
                orderBy: {
                    createdAt: 'desc'
                }
            }),
            this.prisma.analysis.count({
                where: { userId }
            })
        ]);

        return {
            analyses,
            total,
            page,
            limit,
            totalPages: Math.ceil(total / limit)
        };
    }

    async updateAnalysisStatus(analysisId, status, analysisData = null) {
        const updateData = { status };
        if (analysisData) {
            updateData.analysisData = analysisData;
            updateData.updatedAt = new Date();
        }

        return await this.prisma.analysis.update({
            where: { id: analysisId },
            data: updateData
        });
    }
}
```

### 2. 채널 데이터 Repository
```javascript
// 구현 위치: src/database/repositories/channelRepository.js
// 구현 클래스: ChannelRepository

class ChannelRepository {
    constructor(prisma) {
        this.prisma = prisma;
    }

    async findOrCreateChannel(channelData) {
        const { channelId, channelName } = channelData;
        
        let channel = await this.prisma.channel.findUnique({
            where: { channelId }
        });

        if (!channel) {
            channel = await this.prisma.channel.create({
                data: {
                    channelId,
                    channelName,
                    isVerified: false
                }
            });
        }

        return channel;
    }

    async updateChannelStats(channelId, stats) {
        return await this.prisma.channel.update({
            where: { channelId },
            data: {
                subscriberCount: stats.subscriberCount,
                viewCount: stats.viewCount,
                updatedAt: new Date()
            }
        });
    }

    async findChannelsByCredibility(minScore, limit = 20) {
        return await this.prisma.channel.findMany({
            where: {
                videos: {
                    some: {
                        analyses: {
                            some: {
                                overallScore: {
                                    gte: minScore
                                }
                            }
                        }
                    }
                }
            },
            include: {
                _count: {
                    select: {
                        videos: true
                    }
                }
            },
            orderBy: {
                videos: {
                    _count: 'desc'
                }
            },
            take: limit
        });
    }
}
```

## 🔧 **데이터베이스 초기화 및 마이그레이션**

### 1. 초기화 스크립트
```javascript
// 구현 위치: src/database/init.js
// 구현 함수: initializeDatabase()

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function initializeDatabase() {
    try {
        console.log('데이터베이스 연결 확인 중...');
        await prisma.$connect();
        console.log('✅ 데이터베이스 연결 성공');

        console.log('데이터베이스 마이그레이션 실행 중...');
        await prisma.$executeRaw`SELECT 1`;
        console.log('✅ 마이그레이션 완료');

        console.log('시드 데이터 생성 중...');
        await createSeedData();
        console.log('✅ 시드 데이터 생성 완료');

    } catch (error) {
        console.error('❌ 데이터베이스 초기화 실패:', error);
        throw error;
    } finally {
        await prisma.$disconnect();
    }
}

async function createSeedData() {
    // 기본 사용자 생성
    const adminUser = await prisma.user.upsert({
        where: { email: 'admin@infoguard.com' },
        update: {},
        create: {
            email: 'admin@infoguard.com',
            name: 'Admin User',
            passwordHash: '$2b$10$...', // 해시된 비밀번호
            role: 'admin'
        }
    });

    // 테스트 채널 생성
    const testChannel = await prisma.channel.upsert({
        where: { channelId: 'UC_test_channel' },
        update: {},
        create: {
            channelId: 'UC_test_channel',
            channelName: 'Test Channel',
            isVerified: true
        }
    });

    console.log('시드 데이터 생성 완료:', { adminUser, testChannel });
}

module.exports = { initializeDatabase };
```

### 2. 마이그레이션 관리
```bash
# Prisma 마이그레이션 명령어
npx prisma migrate dev --name init
npx prisma migrate deploy
npx prisma generate
npx prisma db seed
```

## 📊 **데이터베이스 모니터링**

### 1. 연결 풀 모니터링
```javascript
// 구현 위치: src/database/monitoring/dbMonitor.js
// 구현 클래스: DatabaseMonitor

class DatabaseMonitor {
    constructor(prisma) {
        this.prisma = prisma;
        this.metrics = {
            totalConnections: 0,
            activeConnections: 0,
            idleConnections: 0,
            queryCount: 0,
            slowQueries: 0
        };
    }

    async getConnectionStats() {
        try {
            const result = await this.prisma.$queryRaw`
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            `;
            
            return result[0];
        } catch (error) {
            console.error('연결 통계 조회 실패:', error);
            return null;
        }
    }

    async getSlowQueries() {
        try {
            const result = await this.prisma.$queryRaw`
                SELECT 
                    query,
                    mean_exec_time,
                    calls,
                    total_exec_time
                FROM pg_stat_statements 
                WHERE mean_exec_time > 1000
                ORDER BY mean_exec_time DESC 
                LIMIT 10
            `;
            
            return result;
        } catch (error) {
            console.error('느린 쿼리 조회 실패:', error);
            return [];
        }
    }

    async getTableStats() {
        try {
            const result = await this.prisma.$queryRaw`
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            `;
            
            return result;
        } catch (error) {
            console.error('테이블 통계 조회 실패:', error);
            return [];
        }
    }
}
```

### 2. 백업 스크립트
```bash
#!/bin/bash
# 구현 위치: src/database/monitoring/backup.sh

BACKUP_DIR="/backup/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="infoguard"
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# PostgreSQL 백업 실행
pg_dump -h localhost -U postgres -d $DB_NAME > $BACKUP_FILE

# 압축
gzip $BACKUP_FILE

# 30일 이상 된 백업 파일 삭제
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "백업 완료: ${BACKUP_FILE}.gz"
```

## 🚀 **성능 최적화 전략**

### 1. 쿼리 최적화
```javascript
// N+1 문제 해결을 위한 include 사용
async function getAnalysesWithDetails(videoIds) {
    return await prisma.analysis.findMany({
        where: {
            videoId: { in: videoIds }
        },
        include: {
            video: {
                include: {
                    channel: true
                }
            },
            user: {
                select: {
                    id: true,
                    name: true
                }
            }
        }
    });
}

// 페이지네이션 최적화
async function getPaginatedAnalyses(page, limit, filters = {}) {
    const skip = (page - 1) * limit;
    
    const [analyses, total] = await Promise.all([
        prisma.analysis.findMany({
            where: filters,
            skip,
            take: limit,
            orderBy: { createdAt: 'desc' }
        }),
        prisma.analysis.count({ where: filters })
    ]);

    return { analyses, total, page, limit };
}
```

### 2. 인덱스 최적화
```sql
-- 부분 인덱스 (활성 사용자만)
CREATE INDEX idx_users_active ON users(id) WHERE is_active = true;

-- 함수 인덱스 (날짜 범위 검색)
CREATE INDEX idx_analyses_date_range ON analyses(created_at) 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';

-- GIN 인덱스 (JSONB 검색)
CREATE INDEX idx_analyses_data_gin ON analyses USING GIN (analysis_data);
```

## 🎯 **구현 완료 체크리스트**

- [ ] PostgreSQL 스키마 설계
- [ ] Prisma ORM 설정
- [ ] 기본 테이블 구조
- [ ] Repository 패턴 구현
- [ ] Redis 캐싱 전략
- [ ] 데이터베이스 연결 관리
- [ ] 기본 모니터링 시스템

- [ ] 고급 인덱스 최적화
- [ ] 백업 자동화
- [ ] 성능 메트릭 대시보드

- [ ] 데이터 마이그레이션 스크립트
- [ ] 고급 백업 전략
- [ ] 데이터 압축 및 아카이빙
- [ ] 크로스 리전 복제
- [ ] 자동 스케일링
