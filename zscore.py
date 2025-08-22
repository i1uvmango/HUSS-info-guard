import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# 예시 데이터 생성
# 각 컬럼은 0~100 점수, 'trust_label'은 실제 신뢰도 라벨 (0~1)
data = pd.DataFrame({
    'fact_score': np.random.uniform(0, 100, 100),
    'bias_score': np.random.uniform(0, 100, 100),
    'sentiment_score': np.random.uniform(0, 100, 100),
    'metadata_score': np.random.uniform(0, 100, 100),
    'trust_label': np.random.uniform(0, 1, 100)
})

# 입력과 출력 정의
X = data[['fact_score', 'bias_score', 'sentiment_score', 'metadata_score']]
y = data['trust_label']

# 학습/검증 데이터 분리
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 선형 회귀 모델 학습
model = LinearRegression()
model.fit(X_train, y_train)

# 학습된 가중치 확인 (w1~w4)와 절편
w1, w2, w3, w4 = model.coef_
intercept = model.intercept_
print(f"가중치 w1~w4: {w1:.3f}, {w2:.3f}, {w3:.3f}, {w4:.3f}")
print(f"절편: {intercept:.3f}")

# 테스트 데이터 예측 및 MSE 확인
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
print(f"테스트 MSE: {mse:.4f}")

# 새로운 콘텐츠 점수로 신뢰도 계산 예시
new_content = {
    'fact_score': 85,
    'bias_score': 20,
    'sentiment_score': 30,
    'metadata_score': 50
}

# 점수를 배열로 변환
X_new = np.array([[new_content['fact_score'], new_content['bias_score'],
                   new_content['sentiment_score'], new_content['metadata_score']]])

# 신뢰도 예측
final_score = model.predict(X_new)[0]
print(f"예측된 최종 신뢰도: {final_score:.3f}")
