# AI 모델 구현 계획

## 🎯 **AI 모델 개요**
Info-Guard의 AI 모델은 YouTube 영상의 신뢰도를 다각도로 분석하는 핵심 시스템입니다. 감정 분석, 편향 감지, 팩트 체킹, 콘텐츠 분류 등을 통해 종합적인 신뢰도 점수를 산출합니다.

## 🏗️ **AI 모델 아키텍처**

### 1. 모델 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Text    │    │  Preprocessing  │    │   AI Models     │
│   (자막/설명)     │───►│   (정규화/토큰화)   │───►│   (분석 엔진)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Text Utils    │    │  Score Fusion   │
                       │   (유틸리티)      │    │   (점수 통합)     │
                       └─────────────────┘    └─────────────────┘
```

### 2. 디렉토리 구조
```
src/python-server/app/ai/
├── __init__.py
├── base.py              # 기본 모델 클래스
├── sentiment.py         # 감정 분석
├── bias.py             # 편향 감지
├── credibility.py      # 신뢰도 분석
├── fact_checker.py     # 팩트 체커
├── classifier.py       # 콘텐츠 분류
└── ensemble.py         # 앙상블 모델
```

## 🤖 **핵심 AI 모델**

### 1. 감정 분석 모델 (Sentiment Analysis)
```python
# 구현 위치: src/python-server/app/ai/sentiment.py
# 구현 클래스: SentimentAnalyzer

class SentimentAnalyzer(BaseModel):
    def __init__(self):
        self.model = self._load_model()
        self.tokenizer = self._load_tokenizer()
    
    def analyze(self, text: str) -> Dict[str, float]:
        """텍스트 감정 분석"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        
        # 감정 점수 계산 (-100 ~ 100)
        sentiment_score = self._calculate_sentiment_score(outputs)
        
        return {
            "sentiment_score": sentiment_score,
            "confidence": self._get_confidence(outputs),
            "emotions": self._extract_emotions(outputs)
        }
    
    def _calculate_sentiment_score(self, outputs) -> float:
        """감정 점수 계산"""
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        
        # 긍정/부정/중립 확률
        positive_prob = probs[0][1].item()
        negative_prob = probs[0][2].item()
        neutral_prob = probs[0][0].item()
        
        # -100 ~ 100 점수로 변환
        score = (positive_prob - negative_prob) * 100
        return round(score, 2)
```

### 2. 편향 감지 모델 (Bias Detection)
```python
# 구현 위치: src/python-server/app/ai/bias.py
# 구현 클래스: BiasDetector

class BiasDetector(BaseModel):
    def __init__(self):
        self.bias_keywords = self._load_bias_keywords()
        self.political_terms = self._load_political_terms()
    
    def detect_bias(self, text: str) -> Dict[str, Any]:
        """편향성 감지"""
        bias_score = 0
        bias_types = []
        
        # 키워드 기반 편향 감지
        keyword_bias = self._detect_keyword_bias(text)
        bias_score += keyword_bias['score']
        bias_types.extend(keyword_bias['types'])
        
        # 정치적 편향 감지
        political_bias = self._detect_political_bias(text)
        bias_score += political_bias['score']
        bias_types.extend(political_bias['types'])
        
        # 언어적 편향 감지
        linguistic_bias = self._detect_linguistic_bias(text)
        bias_score += linguistic_bias['score']
        bias_types.extend(linguistic_bias['types'])
        
        return {
            "bias_score": max(-100, min(100, bias_score)),  # -100 ~ 100
            "bias_types": list(set(bias_types)),
            "confidence": self._calculate_confidence(bias_score),
            "details": {
                "keyword_bias": keyword_bias,
                "political_bias": political_bias,
                "linguistic_bias": linguistic_bias
            }
        }
    
    def _detect_keyword_bias(self, text: str) -> Dict[str, Any]:
        """키워드 기반 편향 감지"""
        bias_score = 0
        bias_types = []
        
        text_lower = text.lower()
        
        # 극단적 표현 감지
        extreme_words = ['절대', '완벽', '최고', '최악', '완전히', '전혀']
        for word in extreme_words:
            if word in text_lower:
                bias_score += 15
                bias_types.append('extreme_language')
        
        # 감정적 표현 감지
        emotional_words = ['충격', '폭로', '충격적', '놀라운', '믿을 수 없는']
        for word in emotional_words:
            if word in text_lower:
                bias_score += 10
                bias_types.append('emotional_language')
        
        return {
            "score": bias_score,
            "types": bias_types
        }
```

### 3. 신뢰도 분석 모델 (Credibility Analyzer)
```python
# 구현 위치: src/python-server/app/ai/credibility.py
# 구현 클래스: CredibilityAnalyzer

class CredibilityAnalyzer(BaseModel):
    def __init__(self):
        self.fact_checker = FactChecker()
        self.bias_detector = BiasDetector()
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def analyze_credibility(self, text: str, metadata: Dict = None) -> Dict[str, Any]:
        """종합 신뢰도 분석"""
        results = {}
        
        # 팩트 체킹
        fact_check_result = self.fact_checker.check_facts(text)
        results['fact_check'] = fact_check_result
        
        # 편향성 분석
        bias_result = self.bias_detector.detect_bias(text)
        results['bias'] = bias_result
        
        # 감정 분석
        sentiment_result = self.sentiment_analyzer.analyze(text)
        results['sentiment'] = sentiment_result
        
        # 종합 신뢰도 점수 계산
        overall_score = self._calculate_overall_score(results)
        
        return {
            "overall_credibility": overall_score,
            "fact_check_score": fact_check_result['score'],
            "bias_score": bias_result['bias_score'],
            "sentiment_score": sentiment_result['sentiment_score'],
            "detailed_analysis": results,
            "confidence": self._calculate_confidence(results)
        }
    
    def _calculate_overall_score(self, results: Dict) -> float:
        """종합 신뢰도 점수 계산"""
        fact_score = results['fact_check']['score'] * 0.4      # 40% 가중치
        bias_score = (100 - abs(results['bias']['bias_score'])) * 0.3  # 30% 가중치
        sentiment_score = (100 - abs(results['sentiment']['sentiment_score'])) * 0.2  # 20% 가중치
        metadata_score = self._calculate_metadata_score(results.get('metadata', {})) * 0.1  # 10% 가중치
        
        total_score = fact_score + bias_score + sentiment_score + metadata_score
        return max(0, min(100, round(total_score, 2)))
```

### 4. 팩트 체커 (Fact Checker)
```python
# 구현 위치: src/python-server/app/ai/fact_checker.py
# 구현 클래스: FactChecker

class FactChecker(BaseModel):
    def __init__(self):
        self.verification_sources = self._load_verification_sources()
        self.fact_patterns = self._load_fact_patterns()
    
    def check_facts(self, text: str) -> Dict[str, Any]:
        """사실 여부 검증"""
        facts = self._extract_facts(text)
        verified_facts = []
        unverified_facts = []
        
        for fact in facts:
            verification_result = self._verify_fact(fact)
            if verification_result['verified']:
                verified_facts.append(verification_result)
            else:
                unverified_facts.append(verification_result)
        
        # 팩트 체크 점수 계산
        fact_check_score = self._calculate_fact_check_score(verified_facts, unverified_facts)
        
        return {
            "score": fact_check_score,
            "verified_facts": verified_facts,
            "unverified_facts": unverified_facts,
            "total_facts": len(facts),
            "verification_rate": len(verified_facts) / len(facts) if facts else 0
        }
    
    def _extract_facts(self, text: str) -> List[str]:
        """텍스트에서 사실 추출"""
        facts = []
        
        # 숫자 기반 사실 패턴
        number_patterns = [
            r'(\d+)\s*(명|개|건|%|원|달러|시간|분|초)',
            r'(\d{4})년\s*(\d{1,2})월',
            r'(\d+)월\s*(\d+)일'
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text)
            facts.extend([f"숫자 정보: {match}" for match in matches])
        
        # 날짜 기반 사실 패턴
        date_patterns = [
            r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
            r'(\d{1,2})월\s*(\d{1,2})일'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            facts.extend([f"날짜 정보: {match}" for match in matches])
        
        return facts
```

## 🔧 **모델 최적화 및 성능**

### 1. 배치 처리
```python
# 구현 위치: src/python-server/app/services/batch_processor.py
# 구현 클래스: BatchProcessor

class BatchProcessor:
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.models = self._initialize_models()
    
    async def process_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """배치 단위로 텍스트 처리"""
        results = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = await self._process_single_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def _process_single_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """단일 배치 처리"""
        tasks = []
        
        for text in texts:
            task = self._analyze_single_text(text)
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks)
        return batch_results
    
    async def _analyze_single_text(self, text: str) -> Dict[str, Any]:
        """단일 텍스트 분석"""
        start_time = time.time()
        
        # 병렬로 여러 모델 실행
        sentiment_task = self.models['sentiment'].analyze(text)
        bias_task = self.models['bias'].detect_bias(text)
        credibility_task = self.models['credibility'].analyze_credibility(text)
        
        results = await asyncio.gather(sentiment_task, bias_task, credibility_task)
        
        processing_time = (time.time() - start_time) * 1000  # ms
        
        return {
            "text": text,
            "sentiment": results[0],
            "bias": results[1],
            "credibility": results[2],
            "processing_time": processing_time
        }
```

### 2. 모델 캐싱
```python
# 구현 위치: src/python-server/app/services/cache.py
# 구현 클래스: AnalysisCache

class AnalysisCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1시간
    
    async def get_cached_analysis(self, text_hash: str) -> Optional[Dict]:
        """캐시된 분석 결과 조회"""
        cache_key = f"analysis:{text_hash}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def cache_analysis_result(self, text_hash: str, result: Dict):
        """분석 결과 캐싱"""
        cache_key = f"analysis:{text_hash}"
        await self.redis.setex(
            cache_key,
            self.cache_ttl,
            json.dumps(result, ensure_ascii=False)
        )
    
    def _generate_text_hash(self, text: str) -> str:
        """텍스트 해시 생성"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
```

## 🎯 **구현 완료 체크리스트**

- [ ] 기본 모델 클래스 구조
- [ ] 감정 분석 모델
- [ ] 편향 감지 모델
- [ ] 신뢰도 분석 모델
- [ ] 팩트 체커 기본 구조
- [ ] 배치 처리 시스템
- [ ] 모델 캐싱 시스템

- [ ] 팩트 체커 완성
- [ ] 콘텐츠 분류 모델
- [ ] 모델 성능 최적화

- [ ] 모델 정확도 평가
- [ ] 자동 모델 업데이트
- [ ] A/B 테스트 시스템
- [ ] 모델 버전 관리