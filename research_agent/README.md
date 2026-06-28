# Multi-Agent Research Automation System

## 구조
```
research_agent/
├── main.py                  # 진입점 (CLI)
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py          # 전역 설정 (모델, API, 경로)
├── core/
│   ├── pipeline.py          # 6-stage 오케스트레이터
│   ├── state.py             # 에이전트 간 공유 상태
│   ├── base_agent.py        # 베이스 클래스
│   └── logger.py            # 로깅
├── agents/
│   ├── manager.py           # Stage 1: 연구 계획
│   ├── searcher.py          # Stage 2: 병렬 웹 검색
│   ├── summarizer.py        # Stage 2: 요약·분류
│   ├── ideation.py          # Stage 3: 아이디어 생성·평가
│   ├── executor.py          # Stage 4: 실험 설계·코드 생성
│   ├── reviewer.py          # Stage 5: Multi-persona 리뷰
│   └── writer.py            # Stage 6: 최종 문서 작성
├── prompts/
│   ├── academic/            # 학술 모드 프롬프트
│   └── strategy/            # AI전략 모드 프롬프트
├── outputs/
│   ├── papers/              # 논문 초안 출력
│   └── reports/             # 전략 리포트 출력
└── logs/                    # 실행 로그 + 상태 JSON
```

## 설치
```bash
pip install -r requirements.txt
cp .env.example .env
# .env에 ANTHROPIC_API_KEY 입력
```

## 실행
```bash
# 학술 논문 연구
python main.py --mode academic --topic "ViT vs CNN image classification survey"

# AI 전략 리포트
python main.py --mode strategy --topic "생성형 AI 규제 동향 분석 2025"

# 옵션
python main.py --mode academic --topic "..." --max-papers 20 --max-revisions 2 --verbose
```

## 에이전트 구조
- **Manager**: 연구 전략 수립 (Sonnet)
- **Searcher**: 병렬 웹 검색 × N (Haiku + web_search tool)
- **Summarizer**: 병렬 요약·분류 (Haiku)
- **Ideation**: 아이디어 생성 → Novelty 평가 → 최적 선정 (Sonnet)
- **Executor**: 실험 설계 + Python 코드 생성 (Sonnet)
- **Reviewer**: Methodology Hawk + Novelty Skeptic + Impact Evaluator 앙상블 (Sonnet)
- **Writer**: 최종 논문/리포트 작성 (Sonnet)
